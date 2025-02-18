from video_processing import os, yt_dlp, get_file_path

def download_youtube_video(video_url, filename="downloaded_video.mp4"):
    output_path = get_file_path(filename)

    # 기존 파일이 존재하면 삭제
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"🗑 기존 파일 삭제: {output_path}")

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    print(f"✅ 다운로드 완료: {output_path}")
    return output_path