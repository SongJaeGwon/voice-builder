from video_processing import os, yt_dlp, get_file_path
import re

def download_youtube_video(video_url, filename="downloaded_video.mp4"):
    output_path = get_file_path(filename)

    # 기존 파일이 존재하면 삭제
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"🗑 기존 파일 삭제: {output_path}")

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:


        ydl.download([video_url])

    print(f"✅ 다운로드 완료: {output_path}")
    return output_path

def extract_whisper_prompt_from_youtube(video_url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)

        extract_key_from_info_dict = ['tags', 'description', 'title']
        values = []
        for key in extract_key_from_info_dict:
            value = info_dict.get(key, '')
            if isinstance(value, list):
                # 리스트인 경우, 내부 요소들을 join해서 하나의 문자열로 만듦
                value = ' '.join(value)
            values.append(value)
        dumped_text = ' '.join(values)

        # 2. 모든 특수문자, 이모지 등 제거
        text = dumped_text.replace('\n', ' ')
        clean_text = re.sub(r'[^\w\s]', '', text)
        words = clean_text.split()
        unique_words = list(dict.fromkeys(words))

        result = ', '.join(unique_words)
        print(result)
        return result