from video_processing import subprocess, get_file_path

def extract_audio_from_video(video_file, filename="trimmed_audio.mp3"):
    output_path = get_file_path(filename)
    command = f"ffmpeg -i {video_file} -q:a 0 -map a {output_path} -loglevel error -y"
    subprocess.run(command, shell=True, check=True)
    return output_path

def audio_preprocessing(audio_file, filename="preprocessed_audio.wav"):
    output_path = get_file_path(filename)

    # 1️⃣ 16kHz, Mono 변환 (FFmpeg)
    command = f"ffmpeg -i {audio_file} -acodec pcm_s16le -ac 1 -ar 16000 {output_path} -loglevel error -y"
    subprocess.run(command, shell=True, check=True)

    return output_path