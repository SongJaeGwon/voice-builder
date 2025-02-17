from video_processing import subprocess, get_file_path

def trim_video(input_file, filename="trimmed_video.mp4", start_time="00:00:14", duration="30"):
    output_file = get_file_path(filename)
    command = f"ffmpeg -i {input_file} -ss {start_time} -t {duration} -c:v copy -c:a copy {output_file} -y"
    subprocess.run(command, shell=True)
    return output_file