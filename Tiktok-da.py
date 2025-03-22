from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import re
import os
import uuid
import logging
from flask_cors import CORS
import time
from urllib.parse import urlparse
import shutil

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary storage for downloaded files
DOWNLOAD_FOLDER = '/tmp/tiktok_downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def sanitize_filename(filename):
    # Remove special characters and non-Arabic/English characters
    filename = re.sub(r'[^\w\s.-أ-يءؤةئآإا]', '', filename)
    # Replace spaces with underscores
    filename = re.sub(r'\s+', '_', filename)
    # Limit filename length
    return filename[:80]

def extract_username_from_url(url):
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        # TikTok URLs typically have the username as the first path component
        if len(path_parts) > 0:
            return path_parts[0]
        return None
    except:
        return None

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
            
        tiktok_url = data['url']
        logger.info(f"Received download request for URL: {tiktok_url}")
        
        # Generate unique ID for this download
        download_id = str(uuid.uuid4())
        download_path = os.path.join(DOWNLOAD_FOLDER, download_id)
        
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        # Extract username from URL for better filename
        username = extract_username_from_url(tiktok_url) or "tiktok_user"
            
        # Configure yt-dlp options - FIXED to use dictionary for outtmpl
        ydl_opts = {
            'format': 'best',
            'outtmpl': {
                'default': os.path.join(download_path, '%(title)s.%(ext)s')
            },
            'no_warnings': True,
            'quiet': False,
            'noplaylist': True,
        }
        
        # Download video info first
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting video info for: {tiktok_url}")
            info_dict = ydl.extract_info(tiktok_url, download=False)
            
            if not info_dict:
                return jsonify({'error': 'Could not extract video information'}), 400
                
            # Get video details for better filename
            title = info_dict.get('title', 'video')
            description = info_dict.get('description', '')
            upload_date = info_dict.get('upload_date', '')
            ext = info_dict.get('ext', 'mp4')
            
            # Create meaningful filename
            # Format: username_firstWordsOfTitle_date.mp4
            short_title = ' '.join((title or '').split()[:5])  # First 5 words of title
            date_formatted = ''
            if upload_date and len(upload_date) == 8:
                date_formatted = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            
            custom_filename = f"{username}_{short_title}"
            if date_formatted:
                custom_filename += f"_{date_formatted}"
                
            sanitized_filename = sanitize_filename(custom_filename)
            final_filename = f"{sanitized_filename}.{ext}"
            
            # Update output template with sanitized filename - FIXED to use dictionary
            ydl_opts['outtmpl'] = {
                'default': os.path.join(download_path, final_filename)
            }
            
            # Download the actual video
            logger.info(f"Downloading video as: {final_filename}")
            ydl.download([tiktok_url])
            
            # Verify the file exists
            expected_file_path = os.path.join(download_path, final_filename)
            
            if not os.path.exists(expected_file_path):
                # If the expected filename doesn't exist, look for any file in the directory
                downloaded_files = os.listdir(download_path)
                if not downloaded_files:
                    return jsonify({'error': 'Failed to download video'}), 500
                
                # Take the first file and rename it
                original_file = os.path.join(download_path, downloaded_files[0])
                os.rename(original_file, expected_file_path)
            
            # For this example, we're assuming static file serving
            # In production, use proper cloud storage
            download_url = f"/static/downloads/{download_id}/{final_filename}"
            
            # Static URL for demonstration
            server_base_url = request.url_root.rstrip('/')
            public_url = f"{server_base_url}{download_url}"
            
            logger.info(f"Download successful. File: {final_filename}")
            
            return jsonify({
                'success': True,
                'filename': final_filename,
                'downloadUrl': public_url,
                'title': sanitized_filename
            })
    
    except Exception as e:
        logger.error(f"Error processing download: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/static/downloads/<download_id>/<filename>', methods=['GET'])
def serve_download(download_id, filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, download_id, filename)
    if os.path.exists(file_path):
        return send_from_directory(os.path.dirname(file_path), 
                                  os.path.basename(file_path), 
                                  as_attachment=True,
                                  download_name=filename)
    else:
        return jsonify({'error': 'File not found'}), 404

# Cleanup old downloads (runs every hour)
def cleanup_old_downloads():
    while True:
        try:
            logger.info("Running cleanup of old downloads")
            current_time = time.time()
            for folder in os.listdir(DOWNLOAD_FOLDER):
                folder_path = os.path.join(DOWNLOAD_FOLDER, folder)
                if os.path.isdir(folder_path):
                    folder_time = os.path.getmtime(folder_path)
                    # Delete folders older than 2 hours
                    if current_time - folder_time > 7200:
                        shutil.rmtree(folder_path)
                        logger.info(f"Deleted old download: {folder}")
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")
        
        # Sleep for 1 hour
        time.sleep(3600)

import threading
# Start cleanup in background thread
cleanup_thread = threading.Thread(target=cleanup_old_downloads, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    # Set the port based on environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
