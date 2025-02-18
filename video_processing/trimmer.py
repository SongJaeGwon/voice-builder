from video_processing import subprocess, get_file_path

def trim_video(input_file, start_time, end_time, filename="trimmed_video.mp4"):

    def time_to_seconds(time_str):
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s

    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    duration = end_seconds - start_seconds
    if not isinstance(duration, (int, float)):
        raise ValueError("Duration must be a number")

    output_file = get_file_path(filename)
    command = f"ffmpeg -i {input_file} -ss {start_time} -t {duration} -c:v copy -c:a copy {output_file} -loglevel error -y"
    subprocess.run(command, shell=True)
    return output_file