from video_processing import os, AudioSegment, ElevenLabs, subprocess, parse_srt, get_file_path
from config import ELEVENLABS_API_KEY

def generate_tts_with_timestamps(srt_file, voice_id, filename="tts_audio.mp3"):
    output_path = get_file_path(filename)
    subtitles = parse_srt(srt_file)
    combined_audio = AudioSegment.silent(duration=0)

    for idx, subtitle in enumerate(subtitles):
        text = subtitle["text"]
        start_ms = int(subtitle["start"] * 1000)
        end_ms = int(subtitle["end"] * 1000)
        duration_ms = end_ms - start_ms

        temp_tts_file = f"temp_{idx}.mp3"
        
        generate_speech_with_elevenlabs(text, voice_id, temp_tts_file)

        tts_audio = AudioSegment.from_file(temp_tts_file)
        tts_duration = len(tts_audio)

        print(f"📌 [{idx}] 음성 파일 생성")
        print(f"   ▶ 원본 SRT 타임스탬프: {subtitle['start']}s ~ {subtitle['end']}s ({duration_ms}ms)")
        print(f"   ▶ 생성된 음성 길이: {tts_duration / 1000:.2f}s")

        if tts_duration > duration_ms:
            speed_factor = tts_duration / duration_ms
            adjusted_tts_file = f"adjusted_{idx}.mp3"

            # FFmpeg을 이용해 배속 조정
            adjust_audio_speed(temp_tts_file, adjusted_tts_file, speed_factor)

            print(f"   ▶ 길이 초과 → {speed_factor:.2f}배속 적용 (FFmpeg 사용)")

            # 변환된 오디오 다시 불러오기
            tts_audio = AudioSegment.from_file(adjusted_tts_file)
            os.remove(adjusted_tts_file)
        elif tts_duration < duration_ms:
            silence = AudioSegment.silent(duration=duration_ms - tts_duration)
            tts_audio = tts_audio + silence

        current_duration = len(combined_audio)
        audio_start = current_duration
        audio_end = audio_start + len(tts_audio)

        if start_ms > current_duration:
            gap = AudioSegment.silent(duration=start_ms - current_duration)
            combined_audio += gap

        combined_audio += tts_audio

        print(f"   🔍 실제 음성 파일 타임스탬프: {audio_start / 1000:.2f}s ~ {audio_end / 1000:.2f}s")

        os.remove(temp_tts_file)

    combined_audio.export(output_path, format="mp3")

    return output_path

def generate_speech_with_elevenlabs(text, voice_id, output_audio):
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    audio_generator = client.text_to_speech.convert(
        voice_id=voice_id,
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_multilingual_v2"
    )
    audio_bytes = b"".join(audio_generator)

    with open(output_audio, "wb") as f:
        f.write(audio_bytes)

def adjust_audio_speed(input_audio, output_audio, speed_factor):
    command = [
        "ffmpeg", "-i", input_audio, 
        "-filter:a", f"atempo={speed_factor}", 
        "-vn", output_audio
    ]
    subprocess.run(command, check=True)