import os
import re
import yt_dlp
import json
import subprocess
import requests
import whisperx
import torch
import openai
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from dotenv import load_dotenv
from huggingface_hub import login

# 🔹 .env 파일 로드
load_dotenv()

# 🔹 환경 변수 가져오기
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
API_URL = os.getenv("API_URL")
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
OPEN_AI = os.getenv("OPEN_AI")

video_url = "https://www.youtube.com/watch?v=cQ0g6RHB4wA"  # 변환할 유튜브 영상 링크
# target_language = "ZH-HANT"  # 번역할 언어 (예: 일본어)
target_language = "KO"  # 번역할 언어 (예: 일본어)
voice_id = "ir1CeAgkMhxW2txdJpxQ"  # ElevenLabs에서 학습한 목소리 ID 입력

def download_youtube_video(video_url, output_filename="downloaded_video.mp4"):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_filename,
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    return output_filename

def trim_video(input_file, output_file="trimmed_video.mp4", start_time="00:00:00", duration="300"):
    command = f"ffmpeg -i {input_file} -ss {start_time} -t {duration} -c:v copy -c:a copy {output_file} -y"
    subprocess.run(command, shell=True)
    return output_file

def extract_audio_from_video(video_file, audio_output="audio.mp3"):
    command = f"ffmpeg -i {video_file} -q:a 0 -map a {audio_output} -y"
    subprocess.run(command, shell=True)
    return audio_output

def separate_background_audio(input_file, output_file="background_audio.mp3"):
    """
    Demucs를 이용해 오디오 파일에서 보컬 트랙을 분리하는 함수.
    기본적으로 demucs는 지정한 output_dir에 분리된 파일들을 저장합니다.

    :param input_file: 원본 오디오 파일 (예: audio.mp3)
    :param output_dir: Demucs가 결과를 저장할 기본 디렉토리 (기본값 "separated")
    :return: 분리된 보컬 파일의 경로 (예: separated/{base_name}/vocals.wav)
    """
    command = f"demucs --two-stems=vocals --out=. --filename=out.mp3 --mp3 {input_file}"
    subprocess.run(command, shell=True, check=True)

    return output_file

def transcribe_audio_whisper(audio_file, model="whisper-1"):
    """
    OpenAI Whisper API를 사용하여 오디오 파일을 텍스트로 변환
    """
    client = openai.OpenAI(api_key=OPEN_AI)  # 최신 방식으로 클라이언트 초기화

    # 🔹 OpenAI Whisper API 요청
    with open(audio_file, "rb") as file:
        response = client.audio.transcriptions.create(
            model=model,
            file=file,
            response_format="verbose_json",  # JSON 형식으로 결과 요청
        )

    # 🔹 JSON으로 변환 (필수)
    response_json = response.model_dump()  # dict() 대신 최신 버전에서는 model_dump() 사용

    # 🔹 변환된 데이터 저장 (JSON)
    with open("transcription_whisper.json", "w", encoding="utf-8") as f:
        json.dump(response_json, f, indent=4, ensure_ascii=False)

    return response_json

def transcribe_audio_whisperx(audio_file, language="ko", device=None, num_speakers=None):
    """
    WhisperX를 사용하여 오디오 파일을 텍스트로 변환하고 SRT 파일을 생성 (다중 화자 포함)
    """

    # 🔹 디바이스 설정 (Mac 환경에서는 CPU 또는 MPS 사용)
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # GPU 사용 가능하면 CUDA, 없으면 CPU

    # 🔹 WhisperX 모델 로드
    model = whisperx.load_model("large-v2", "cpu", compute_type="float32")

    audio = whisperx.load_audio(audio_file)

    # 🔹 오디오 변환 (STT 수행)
    transcription = model.transcribe(audio)

    # 🔹 Align (음성-텍스트 정렬)
    align_model, align_metadata = whisperx.load_align_model(language_code=transcription["language"], device=device)
    whisper_results = whisperx.align(transcription["segments"], align_model, align_metadata, audio, device, return_char_alignments=False)

    # 🔥 다중 화자(Speaker Diarization) 모델 로드 (Hugging Face 토큰 포함)
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=HF_TOKEN, device=device)

    # 🔹 화자 분리 실행
    diarization_result = diarize_model(audio, num_speakers=num_speakers) if num_speakers else diarize_model(audio)

    # 🔹 STT 결과와 화자 정보 동기화
    whisper_results = whisperx.assign_word_speakers(diarization_result, whisper_results)

    # 🔹 변환된 데이터 저장 (JSON)
    with open("transcription_whisperx.json", "w", encoding="utf-8") as f:
        json.dump(whisper_results, f, indent=4, ensure_ascii=False)

    return whisper_results

def seconds_to_srt_time(seconds):
    """ 초 단위를 SRT 형식 (HH:MM:SS,mmm)으로 변환 """
    millisec = int((seconds % 1) * 1000)
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

def create_srt_v1(transcription, output_srt="output.srt"):
    """
    Whisper 변환 결과를 SRT 파일로 저장
    """
    if "segments" not in transcription:
        print("⚠️ 변환된 자막 데이터가 없습니다.")
        return

    with open(output_srt, "w", encoding="utf-8") as f:
        for idx, segment in enumerate(transcription["segments"]):
            start_time = seconds_to_srt_time(segment["start"])
            end_time = seconds_to_srt_time(segment["end"])
            text = segment["text"]

            f.write(f"{idx+1}\n{start_time} --> {end_time}\n{text}\n\n")

    print(f"✅ SRT 파일 생성 완료: {output_srt}")

def translate_text(text, src_lang="KO", target_lang="JA"):
    """
    DeepL API를 사용하여 텍스트 번역
    :param text: 번역할 원본 텍스트
    :param src_lang: 원본 언어 코드 (예: "KO" -> 한국어)
    :param target_lang: 목표 언어 코드 (예: "JA" -> 일본어)
    :return: 번역된 텍스트
    """
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"}
    data = {
        "text": [text],  # 리스트 형태로 전달해야 함
        "source_lang": src_lang.upper(),  # DeepL은 대문자 언어 코드 사용
        "target_lang": target_lang.upper()
    }

    response = requests.post(API_URL, headers=headers, data=data)

    if response.status_code == 200:
        result = response.json()
        return result["translations"][0]["text"]  # 번역된 텍스트 반환
    else:
        print("❌ 번역 실패:", response.text)
        return None

def translate_srt(input_srt, output_srt, src_lang="KO", target_lang="JA"):
    """
    DeepL API를 사용하여 SRT 파일을 번역하여 새로운 SRT 파일 생성
    """
    with open(input_srt, "r", encoding="utf-8") as f:
        lines = f.readlines()

    translated_lines = []
    for line in lines:
        if "-->" in line or line.strip().isdigit() or line.strip() == "":
            translated_lines.append(line)  # 시간 및 인덱스는 그대로 유지
        else:
            translated_text = translate_text(line.strip(), src_lang, target_lang)
            translated_lines.append(translated_text + "\n")

    with open(output_srt, "w", encoding="utf-8") as f:
        f.writelines(translated_lines)

    print(f"✅ 번역 완료! 새로운 SRT 파일 저장: {output_srt}")
    return output_srt

# 🔹 Step 5: ElevenLabs API를 이용해 번역된 텍스트를 음성으로 변환
def generate_speech_with_elevenlabs(text, voice_id, output_audio):
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # TTS 변환 실행
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_multilingual_v2"
    )

    # 🔹 제너레이터 데이터를 바이트 형식으로 변환
    audio_bytes = b"".join(audio)  

    # 변환된 오디오 저장
    with open(output_audio, "wb") as f:
        f.write(audio_bytes)

def parse_srt(srt_file):
    """
    SRT 파일을 파싱하여 타임스탬프 및 텍스트를 올바르게 추출
    """
    srt_pattern = re.compile(r"(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]*?)(?=\n\d+\s*\n|\Z)")

    with open(srt_file, "r", encoding="utf-8") as file:
        content = file.read()

    matches = srt_pattern.findall(content)
    subtitles = []

    for _, start, end, text in matches:
        start_seconds = srt_time_to_seconds(start)
        end_seconds = srt_time_to_seconds(end)

        # 🔹 여러 줄의 텍스트를 하나의 줄로 합치기
        text = text.strip().replace("\n", " ")

        subtitles.append({"start": start_seconds, "end": end_seconds, "text": text})

    return subtitles

def srt_time_to_seconds(time_str):
    """SRT 시간 문자열을 초 단위로 변환 (HH:MM:SS,mmm → 초)"""
    hours, minutes, seconds_millis = time_str.split(":")
    seconds, millis = map(int, seconds_millis.split(","))
    return int(hours) * 3600 + int(minutes) * 60 + seconds + millis / 1000

def generate_tts_with_timestamps(srt_file, voice_id, output_audio="final_tts_audio.mp3"):
    """
    번역된 SRT 파일을 기반으로, 타임스탬프를 고려한 음성을 생성하고 하나의 파일로 병합
    """
    subtitles = parse_srt(srt_file)
    
    # 🔹 최종 합칠 오디오 리스트
    combined_audio = AudioSegment.silent(duration=0)
    
    for idx, subtitle in enumerate(subtitles):
        text = subtitle["text"]
        start_time = int(subtitle["start"] * 1000)  # 밀리초 단위로 변환
        end_time = int(subtitle["end"] * 1000)  # 종료 시간 (ms)
        duration = end_time - start_time  # 해당 구간 길이 (ms)

        tts_filename = f"temp_{idx}.mp3"

        # 🔹 ElevenLabs TTS 생성
        generate_speech_with_elevenlabs(text, voice_id, tts_filename)

        # 🔹 TTS 오디오 로드
        tts_audio = AudioSegment.from_file(tts_filename)
        tts_duration = len(tts_audio)  # 실제 생성된 음성 길이 (ms)

        # 🔹 음성 길이 조정
        if tts_duration > duration:
            speed_factor = tts_duration / duration  # 줄여야 하는 배속 비율 계산
            print(f"⚠️ 생성된 TTS({tts_duration}ms)가 원본보다 김({duration}ms), {speed_factor:.2f}배 속도로 빠르게 재생")
            tts_audio = tts_audio.speedup(playback_speed=speed_factor)  # 속도 증가
        elif tts_duration < duration:
            print(f"⚠️ 생성된 TTS({tts_duration}ms)가 원본보다 짧음({duration}ms), 패딩 추가")
            silence = AudioSegment.silent(duration=duration - tts_duration)  # 짧은 경우, 무음 추가
            tts_audio = tts_audio + silence

        # 🔹 음성 삽입 (중간에 공백을 넣어야 함)
        silence_gap = AudioSegment.silent(duration=start_time - len(combined_audio))
        combined_audio = combined_audio + silence_gap + tts_audio

        # 🔹 임시 파일 삭제
        os.remove(tts_filename)

    # 🔹 최종 오디오 파일 저장
    combined_audio.export(output_audio, format="mp3")
    print(f"✅ 타임스탬프가 고려된 음성 파일 생성 완료: {output_audio}")
    return output_audio

# 🔹 Step 6: 새 음성을 원본 영상에 합치기
def merge_audio_with_video(original_video, new_audio, output_video="final_video.mp4"):
    command = f"ffmpeg -i {original_video} -i {new_audio} -c:v copy -map 0:v:0 -map 1:a:0 -shortest {output_video} -y"
    subprocess.run(command, shell=True)
    return output_video

# 🔹 Step 7: 전체 파이프라인 실행
def process_video(video_url, target_language="JA", voice_id="YOUR_VOICE_ID"):
    print("📥 1. 유튜브 영상 다운로드 중...")
    # video_file = download_youtube_video(video_url)

    video_file = "정연_중국어.mp4"

    print("✂️ FFmpeg로 30초 길이로 자르기...")
    trimmed_video = trim_video(video_file)

    print("🎙️ 2. 오디오 추출 중...")
    audio_file = extract_audio_from_video(trimmed_video)

    # Demucs를 실행하여 배경음 트랙 분리
    try:
        print("🎚️ 2-1. Demucs로 보컬 분리 중...")
        separate_background_audio(audio_file)
    except Exception as e:
        print("❌ 보컬 분리 실패:", e)
        return

    print("📝 3. 음성 → 텍스트 변환 중...")
    original_text = transcribe_audio_whisper(audio_file)

    print("📝 4. SRT 파일 생성 중...")
    create_srt_v1(original_text, "transcription.srt")

    print(f"🌍 5. 번역 중... (언어: {target_language})")
    translated_srt = translate_srt("transcription.srt", "translated.srt", src_lang="ZH-HANT", target_lang=target_language)

    if translated_srt is None:
        print("❌ 번역 실패: SRT 파일이 생성되지 않았습니다.")
        return

    print("🔊 6. 타임스탬프 기반 TTS 생성 중...")
    translated_audio = generate_tts_with_timestamps(translated_srt, voice_id)

    # Merge the translated audio with background audio
    print("🎵 6-1. background audio 합치는 중...")
    translated_audio_segment = AudioSegment.from_file(translated_audio)
    background_audio_segment = AudioSegment.from_file("./htdemucs/out.mp3")

    # Ensure both audio segments are the same length
    background_length = len(background_audio_segment)
    translated_length = len(translated_audio_segment)
    if background_length > translated_length:
        background_audio_segment = background_audio_segment[:translated_length]

    final_audio = translated_audio_segment.overlay(background_audio_segment)
    final_audio.export(translated_audio, format="mp3")

    if final_audio:
        print("🎬 7. 새로운 음성을 원본 영상에 합치기...")
        final_video = merge_audio_with_video(trimmed_video, translated_audio)
        print("✅ 변환 완료! 최종 파일:", final_video)
    else:
        print("❌ 오류 발생: 새로운 음성 생성 실패.")

process_video(video_url, target_language, voice_id)