import yt_dlp
import re
import os

def sanitize_filename(filename):
    # إزالة الرموز الخاصة مثل: 🤍🌧️❤
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # تقليص الاسم ليكون أكثر منطقية (اختياري)
    return filename[:100]  # تحديد الحد الأقصى لطول الاسم

def download_tiktok_video(url, save_path):
    # التأكد من أن المسار صحيح
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,  # تحميل فيديو واحد فقط
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),  # تحديد مكان الحفظ
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', 'video')
        sanitized_title = sanitize_filename(title)
        
        # تحديث المسار والاسم مع إضافة المسار الكامل
        ydl_opts['outtmpl'] = os.path.join(save_path, f'{sanitized_title}.%(ext)s')
        
        # إعادة تحميل الفيديو مع الخيارات الجديدة
        with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
            ydl_download.download([url])

if __name__ == "__main__":
    # الحصول على الرابط من المستخدم
    video_url = input("Enter the TikTok video URL: ")

    # تحديد المسار لحفظ الفيديو
    save_path = input("Enter the path where you want to save the video (e.g., /storage/emulated/0/Download): ")

    # بدء التنزيل
    download_tiktok_video(video_url, save_path)
    print("Video downloaded successfully!")
