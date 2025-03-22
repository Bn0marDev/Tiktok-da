from flask import Flask, request, jsonify
import yt_dlp
import re
import os
import uuid
import logging
from flask_cors import CORS

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
    # Remove special characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Limit filename length
    return filename[:100]

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
            
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
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
                
            title = info_dict.get('title', 'tiktok_video')
            ext = info_dict.get('ext', 'mp4')
            sanitized_title = sanitize_filename(title)
            
            # Update output template with sanitized filename
            ydl_opts['outtmpl'] = os.path.join(download_path, f'{sanitized_title}.%(ext)s')
            
            # Download the actual video
            logger.info(f"Downloading video: {sanitized_title}")
            ydl.download([tiktok_url])
            
            # Find the downloaded file
            downloaded_files = os.listdir(download_path)
            if not downloaded_files:
                return jsonify({'error': 'Failed to download video'}), 500
                
            video_filename = downloaded_files[0]
            video_path = os.path.join(download_path, video_filename)
            
            # In a real production environment, you'd save this file to a cloud storage
            # and provide a URL for download. For this example, we'll assume a simple
            # static file serving setup.
            
            # The URL should point to where your files are publicly accessible
            download_url = f"/static/downloads/{download_id}/{video_filename}"
            
            # Static URL for demonstration - in production use cloud storage URLs
            # or proper file serving mechanisms
            server_base_url = request.host_url.rstrip('/')
            public_url = f"{server_base_url}{download_url}"
            
            logger.info(f"Download successful. File: {video_filename}")
            
            return jsonify({
                'success': True,
                'filename': video_filename,
                'downloadUrl': public_url,
                'title': sanitized_title
            })
    
    except Exception as e:
        logger.error(f"Error processing download: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Route to serve downloaded files
@app.route('/static/downloads/<download_id>/<filename>', methods=['GET'])
def serve_download(download_id, filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, download_id, filename)
    if os.path.exists(file_path):
        # Set cache control and content disposition
        response = app.send_static_file(file_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    else:
        return jsonify({'error': 'File not found'}), 404

# Cleanup function to remove old downloads (could be called periodically)
def cleanup_old_downloads():
    import shutil
    import time
    
    current_time = time.time()
    for folder in os.listdir(DOWNLOAD_FOLDER):
        folder_path = os.path.join(DOWNLOAD_FOLDER, folder)
        if os.path.isdir(folder_path):
            # Get folder modification time
            folder_time = os.path.getmtime(folder_path)
            # If older than 1 hour, delete it
            if current_time - folder_time > 3600:
                shutil.rmtree(folder_path)

if __name__ == '__main__':
    # Set the port based on environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
