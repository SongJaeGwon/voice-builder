from video_processing import subprocess, get_file_path

def extract_audio_from_video(video_file, filename="trimmed_audio.mp3"):
    output_path = get_file_path(filename)
    command = f"ffmpeg -i {video_file} -q:a 0 -map a {output_path} -y"
    subprocess.run(command, shell=True, check=True)
    return output_path