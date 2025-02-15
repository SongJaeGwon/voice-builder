from video_processing import os, subprocess, get_file_path

def separate_background_audio(input_file, filename="background_audio.mp3"):
    # 원하는 최종 파일 경로
    final_output_path = get_file_path(filename)
    # 디렉토리와 파일명 분리
    output_dir = os.path.dirname(final_output_path)
    output_basename = os.path.basename(final_output_path)
    
    command = f"demucs --two-stems=vocals --out={output_dir} --filename={output_basename} --mp3 {input_file}"
    subprocess.run(command, shell=True, check=True)

    model_folder = os.path.join(output_dir, "htdemucs")
    possible_output = os.path.join(model_folder, output_basename)
    if os.path.exists(possible_output):
        os.replace(possible_output, final_output_path)
    return final_output_path