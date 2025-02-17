from video_processing import json, openai, SpeakerDiarization, get_file_path
from config import OPEN_AI_TOKEN, HF_TOKEN

diarization_pipeline = SpeakerDiarization.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=HF_TOKEN
)

def transcribe_audio_whisper(audio_file, num_speakers=None, model="whisper-1"):
    client = openai.OpenAI(api_key=OPEN_AI_TOKEN)

    # 🔹 OpenAI Whisper API 요청
    with open(audio_file, "rb") as file:
        response = client.audio.transcriptions.create(
            model=model,
            file=file,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"],
        )

    response_json = response.model_dump()

    with open(get_file_path("transcription_whisper.json"), "w", encoding="utf-8") as f:
        json.dump(response_json, f, indent=4, ensure_ascii=False)

    # 🔹 화자 분리 수행 (Pyannote)
    diarization_result = diarize_audio(audio_file, num_speakers=num_speakers)

    # 🔹 화자 정보와 Whisper 텍스트 매칭
    speaker_segments = match_speakers_with_transcription(diarization_result, response_json)

    output_path = get_file_path("transcription_whisper_speaker.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(speaker_segments, f, indent=4, ensure_ascii=False)

    return speaker_segments

def diarize_audio(audio_file, num_speakers=None):
    """Pyannote를 사용하여 화자 분리 수행"""

    # 🔹 `num_speakers`가 지정된 경우, 해당 값으로 설정
    params = {"num_speakers": num_speakers} if num_speakers else {}

    diarization_result = diarization_pipeline({"uri": "audio", "audio": audio_file}, **params)
    
    speaker_timestamps = []
    for speech_turn, track, speaker in diarization_result.itertracks(yield_label=True):
        speaker_timestamps.append({
            "speaker": speaker,
            "start": speech_turn.start,
            "end": speech_turn.end
        })

    return speaker_timestamps

def match_speakers_with_transcription(
    diarization_result, whisper_response, fill_nearest=False
):
    """
    Whisper의 텍스트와 Pyannote 화자 분리 결과를 매칭하여 'segments' 리스트로 반환
    - 문장(Sentence) 단위 및 단어(Word) 단위 화자 정보 추가
    - Whisper 응답에서 'segments'와 'words'가 따로 제공되므로 이를 병합
    - `fill_nearest=True` 시 가장 가까운 화자를 자동으로 할당
    """
    whisper_segments = whisper_response.get("segments", [])
    whisper_words = whisper_response.get("words", [])

    segments = []

    for seg in whisper_segments:
        start_time = seg["start"]
        end_time = seg["end"]
        text = seg["text"]

        # 🔹 화자 구간과 Whisper 구간의 교집합 계산 (intersection)
        diarization_intersections = [
            {
                "speaker": diarization["speaker"],
                "intersection": max(
                    0, min(diarization["end"], end_time) - max(diarization["start"], start_time)
                )
            }
            for diarization in diarization_result
        ]

        # 🔹 가장 많이 겹치는 화자 찾기
        if diarization_intersections:
            best_match = max(diarization_intersections, key=lambda x: x["intersection"])
            speaker = best_match["speaker"] if best_match["intersection"] > 0 else "Unknown"
        else:
            speaker = "Unknown"

        # 🔹 화자 정보가 없을 경우, `fill_nearest` 옵션에 따라 처리
        if speaker == "Unknown" and fill_nearest:
            closest_speaker = min(
                diarization_result,
                key=lambda x: abs(x["start"] - start_time),
                default=None,
            )
            if closest_speaker:
                speaker = closest_speaker["speaker"]

        # 🔹 현재 `segment`에 해당하는 단어 찾기
        words = []
        for word in whisper_words:
            word_start = word.get("start")
            word_end = word.get("end")

            # 단어가 현재 segment 범위 내에 있는지 확인
            if word_start and word_end and start_time <= word_start <= end_time:
                diarization_intersections = [
                    {
                        "speaker": diarization["speaker"],
                        "intersection": max(
                            0, min(diarization["end"], word_end) - max(diarization["start"], word_start)
                        )
                    }
                    for diarization in diarization_result
                ]

                # 🔹 단어별 가장 많이 겹치는 화자 찾기
                if diarization_intersections:
                    best_match = max(diarization_intersections, key=lambda x: x["intersection"])
                    word_speaker = best_match["speaker"] if best_match["intersection"] > 0 else speaker
                else:
                    word_speaker = speaker

                words.append({
                    "word": word["word"],
                    "start": word_start,
                    "end": word_end,
                    "speaker": word_speaker
                })

        segments.append({
            "speaker": speaker,
            "start": start_time,
            "end": end_time,
            "text": text,
            "words": words
        })

    return {"segments": segments}

def refine_srt_with_gpt(srt_file_path, output_srt_path):
    with open(srt_file_path, "r", encoding="utf-8") as file:
        srt_content = file.read()

    prompt = f"""
    다음은 자막 파일의 내용입니다. 이 자막을 더 자연스럽고 문맥에 맞게 수정해 주세요.
    단어의 의미를 변경하지 않고, 더 읽기 쉽고 자연스럽게 다듬어 주세요.

    **SRT 형식 유지 (번호, 타임스탬프, 텍스트만 포함)**  
    **불필요한 텍스트(예: 코드 블록, ```plaintext 등)는 포함하지 말 것**  
    **자연스럽고 가독성 좋은 문장으로 변환**

    -- 원본 자막 --
    {srt_content}

    -- 변환된 자막 --
    """

    client = openai.OpenAI(api_key=OPEN_AI_TOKEN)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "당신은 자막을 다듬는 전문가입니다."},
                  {"role": "user", "content": prompt}],
        temperature=0.7
    )

    refined_srt = response.choices[0].message.content.strip()

    with open(output_srt_path, "w", encoding="utf-8") as file:
        file.write(refined_srt)

    return output_srt_path