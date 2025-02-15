from video_processing import subprocess, AudioSegment, get_file_path

def merge_audio_with_video(original_video, new_audio, filename="final_video.mp4"):
    output_path = get_file_path(filename)
    command = f"ffmpeg -i {original_video} -i {new_audio} -c:v copy -map 0:v:0 -map 1:a:0 -shortest {output_path} -y"
    subprocess.run(command, shell=True, check=True)
    return output_path

def merge_background_with_tts(tts_audio_path, background_filename="background_audio.mp3", output_format="mp3"):
    
    try:
        # TTS 및 배경음 오디오 로드
        tts_audio_segment = AudioSegment.from_file(tts_audio_path)
        background_audio_segment = AudioSegment.from_file(get_file_path(background_filename))
        
        # 배경음 길이가 TTS보다 길면 TTS 길이에 맞춤
        if len(background_audio_segment) > len(tts_audio_segment):
            background_audio_segment = background_audio_segment[:len(tts_audio_segment)]
        
        # 두 오디오 오버레이 (합성)
        final_audio = tts_audio_segment.overlay(background_audio_segment)
        
        # 최종 오디오를 tts_audio_path에 덮어쓰기
        final_audio.export(tts_audio_path, format=output_format)
        return tts_audio_path
        
    except Exception as e:
        print("❌ 배경음 합성 실패:", e)
        raise