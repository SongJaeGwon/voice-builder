from video_processing.downloader import download_youtube_video
from video_processing.trimmer import trim_video
from video_processing.audio_extractor import extract_audio_from_video
from video_processing.vocal_separation import separate_background_audio
from video_processing.transcription import transcribe_audio_whisper
from video_processing.srt_utils import create_srt
from video_processing.translation import translate_srt
from video_processing.tts import generate_tts_with_timestamps
from video_processing.merging import merge_audio_with_video, merge_background_with_tts
from video_processing.file_manager import get_file_path

def process_video(video_url, source_lang, target_lang, voice_id):

    # 1. 영상 다운로드
    print("📥 1. 유튜브 영상 다운로드 중...")
    video_file = download_youtube_video(video_url)

    # 2. 영상 자르기
    print("2. FFmpeg로 영상 자르기...")
    trimmed_video = trim_video(video_file)
    
    # 3. 오디오 추출
    print("🎙️ 3. 오디오 추출 중...")
    audio_file = extract_audio_from_video(trimmed_video)
    
    # 4. 보컬(배경음) 분리
    print("🎚️ 4. Demucs로 보컬 분리 중...")
    separate_background_audio(audio_file)
    
    # 5. 음성 → 텍스트 변환 (Whisper)
    print("📝 5. 음성 → 텍스트 변환 중...")
    transcription = transcribe_audio_whisper(audio_file)

    # 6. Whisper json -> .srt 파일 변환
    print("📝 6. Whisper json -> .srt 파일 변환...")
    create_srt(transcription)
    
    # 6. SRT 번역 (예: source_lang → target_lang)
    print(f"🌍 6. 번역 중... (언어: {target_lang})")
    translated_srt = translate_srt(get_file_path("transcription.srt"), get_file_path("translated.srt"), source_lang, target_lang)
    
    # 7. 타임스탬프 기반 TTS 생성
    print("🔊 7. 타임스탬프 기반 TTS 생성 중...")
    tts_audio = generate_tts_with_timestamps(translated_srt, voice_id)
    
    # 8. 배경음과 TTS 합성
    print("🎵 8. background audio 합치는 중...")
    merge_background_with_tts(tts_audio)
    
    # 9. 최종 영상과 음성 병합
    print("🎬 9. 새로운 음성을 원본 영상에 합치기...")
    final_video = merge_audio_with_video(trimmed_video, tts_audio)
    
    print("✅ 최종 파일 생성:", final_video)
    return final_video

if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=hSWsDc0h5g8"  # 로컬 파일 경로 또는 다운로드 URL
    source_lang = "KO" # 원본파일 언어
    target_lang = "EN" # 번역할 언어
    voice_id = "ir1CeAgkMhxW2txdJpxQ" # 일레븐랩스 보이스 id

    process_video(video_url, source_lang, target_lang, voice_id)