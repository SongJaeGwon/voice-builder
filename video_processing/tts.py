from video_processing import os, AudioSegment, ElevenLabs, subprocess, torchaudio, torch, requests, parse_srt, get_file_path
from config import ELEVENLABS_API_KEY

def extract_speech_with_elevenlabs(input_audio, output_audio):
    output_path = get_file_path(output_audio)

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # 🎙️ Step 1: ElevenLabs API 호출 (음성만 분리)
    with open(input_audio, "rb") as audio_file:
        audio = client.audio_isolation.audio_isolation(audio=audio_file)
        audio_bytes = b"".join(chunk for chunk in audio)

    temp_audio_path = output_path.replace(".wav", "_temp.wav")

    # 🔽 Step 2: API에서 받은 오디오 저장 (임시 파일)
    with open(temp_audio_path, "wb") as f:
        f.write(audio_bytes)

    # 🔄 Step 3: 오디오를 16kHz 샘플링 속도로 변환
    waveform, sample_rate = torchaudio.load(temp_audio_path)

    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
        waveform = resampler(waveform)

    # 🛠️ Step 4: 길이가 다른 오디오 조각 맞추기 (Padding)
    def pad_audio(waveform, target_length=160000):
        """오디오를 특정 길이로 패딩"""
        current_length = waveform.shape[1]  # 채널 x 샘플 수
        if current_length < target_length:
            pad_size = target_length - current_length
            waveform = torch.nn.functional.pad(waveform, (0, pad_size), mode="constant", value=0)
        return waveform

    padded_waveform = pad_audio(waveform)

    # 🎧 Step 5: 최종 오디오 저장
    torchaudio.save(output_path, padded_waveform, 16000)

    # 🔄 Step 6: 임시 파일 삭제
    os.remove(temp_audio_path)

    return output_path

def generate_tts_with_timestamps(srt_file, speaker_voice_id_list, filename="tts_audio.mp3"):
    output_path = get_file_path(filename)
    subtitles = parse_srt(srt_file)
    combined_audio = AudioSegment.silent(duration=0)
    previous_ids = []

    speaker_voice_map = convert_list_to_speaker_map(speaker_voice_id_list)

    for idx, subtitle in enumerate(subtitles):
        text = subtitle["text"]
        speaker = subtitle["speaker"]
        start_ms = int(subtitle["start"] * 1000)
        end_ms = int(subtitle["end"] * 1000)
        duration_ms = end_ms - start_ms

        # voice_id = SPEAKER_VOICE_MAP.get(speaker, default_voice_id)  # 기본값 적용
        voice_id = speaker_voice_map.get(speaker, speaker_voice_id_list[0])  # 기본값 적용

        temp_tts_file = f"temp_{idx}.mp3"
        
        request_id = generate_speech_with_elevenlabs(text, voice_id, temp_tts_file, previous_ids)
        if request_id:
            previous_ids.append(request_id)  # 새 ID 추가
            previous_ids = previous_ids[-3:]  # 최대 3개까지만 유지

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

            print(f"   ▶ 길이 초과 → {speed_factor:.2f}배속 적용")

            # 변환된 오디오 다시 불러오기
            tts_audio = AudioSegment.from_file(adjusted_tts_file)
            os.remove(adjusted_tts_file)
        elif tts_duration < duration_ms:
            silence = AudioSegment.silent(duration=duration_ms - tts_duration)
            tts_audio = tts_audio + silence

        audio_start = start_ms
        audio_end = audio_start + len(tts_audio)

        if start_ms > len(combined_audio):
            gap = AudioSegment.silent(duration=audio_start - len(combined_audio))
            combined_audio += gap

        combined_audio += tts_audio

        print(f"   🔍 실제 음성 파일 타임스탬프: {audio_start / 1000:.2f}s ~ {audio_end / 1000:.2f}s")

        os.remove(temp_tts_file)

    combined_audio.export(output_path, format="mp3")

    return output_path

def generate_speech_with_elevenlabs(text, voice_id, output_audio, previous_request_ids=None):

    # 요청 본문 구성
    request_data = {
        "voice_id": voice_id,
        "output_format": "mp3_44100_128",
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }

    if previous_request_ids:
        request_data["previous_request_ids"] = previous_request_ids

    # API 요청
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=request_data)

    if response.status_code == 200:
        audio_bytes = response.content

        # 오디오 파일 저장
        with open(output_audio, "wb") as f:
            f.write(audio_bytes)

        # 응답 헤더에서 request_id 추출
        request_id = response.headers.get("request-id")

        return request_id
    else:
        print(f"⚠️ 오류 발생: {response.status_code} - {response.text}")
        return None

def adjust_audio_speed(input_audio, output_audio, speed_factor):
    """
    FFmpeg을 사용하여 속도를 자연스럽게 조정 (rubberband 필터 적용)
    """
    command = [
        "ffmpeg", "-i", input_audio,
        "-filter:a", f"rubberband=pitch=1.0:tempo={speed_factor}",
        "-vn", output_audio, "-loglevel", "error", "-y"
    ]
    subprocess.run(command, check=True)


def convert_list_to_speaker_map(voice_id_list):
    """
    voice_id_list의 각 원소를 SPEAKER_XX 형식의 key에 할당하여 dictionary로 반환합니다.
    예: ['id0', 'id1', 'id2', 'id3', 'id4'] ->
        {
            "SPEAKER_00": "id0",
            "SPEAKER_01": "id1",
            "SPEAKER_02": "id2",
            "SPEAKER_03": "id3",
            "SPEAKER_04": "id4",
        }
    """
    return {f"SPEAKER_{i:02}": voice_id for i, voice_id in enumerate(voice_id_list)}