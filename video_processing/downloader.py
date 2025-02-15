from video_processing import yt_dlp, get_file_path

def download_youtube_video(video_url, filename="downloaded_video.mp4"):
    output_path = get_file_path(filename)
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    return output_path