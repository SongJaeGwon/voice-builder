import os
import re
import gradio as gr

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
OPEN_AI_TOKEN = os.getenv("OPEN_AI_TOKEN")

def get_voice_list():
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    response = client.voices.get_all()
    voices = response.voices

    return {voice.voice_id: voice.name for voice in voices}

# Example usage:
# parse_srt_files('downloads/transcription.srt', 'downloads/translation.srt')()
def selected_upload_method(tab_id):
    """
    Return the ID (or label) of the selected tab
    so we can store it in Gradio state.
    """
    return tab_id

def parse_srt_files(transcription_path, translation_path):
    # 각 블록에서 인덱스, 시간 범위, 스피커, 그리고 대화 텍스트를 추출하는 정규표현식
    pattern = re.compile(
        r'\d+\s*\n'                                                     # 블록 인덱스 (무시)
        r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n'  # 시작 시간과 종료 시간
        r'(.+?)\s*\n'                                                   # 스피커 라인
        r'(.+?)(?=\n\s*\n|\Z)',                                           # 대화 텍스트 (여러 줄일 수 있으므로 비탐욕적)
        re.DOTALL
    )

    def parse(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [
            (
                m.group(1),                # 시작 시간
                m.group(2),                # 종료 시간
                m.group(3).strip(),        # 스피커
                m.group(4).strip().replace('\n', ' ')  # 대화 텍스트 (줄바꿈은 공백으로)
            )
            for m in re.finditer(pattern, content)
        ]

    transcription_entries = parse(transcription_path)
    translation_entries = parse(translation_path)

    combined_entries = [
        [t_start, t_end, t_speaker, t_text, tr_text]
        for (t_start, t_end, t_speaker, t_text), (_, _, _, tr_text) in zip(transcription_entries, translation_entries)
    ]
    return combined_entries

# srt 파일 업데이트
def time_to_seconds(time_str):
    try:
        h, m, s_ms = time_str.split(":")
        s, ms = s_ms.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    except Exception:
        return 0

def write_srt_file(file_path, samples, text_index):
    """
    file_path: 작성할 파일 경로
    samples:   [ [start, end, speaker, original, translation], ... ]
    text_index: 3 -> original, 4 -> translation
    """
    srt_lines = []
    for idx, sample in enumerate(samples, 1):
        start, end = sample[0], sample[1]
        speaker    = sample[2]
        text       = sample[text_index]  # original 또는 translation

        # SRT 블록 형식:
        # 1) 블록 번호
        # 2) 00:00:00,000 --> 00:00:00,500
        # 3) SPEAKER_X
        # 4) 대사 내용
        # 5) 빈 줄 (다음 블록과 구분)
        srt_lines.append(f"{idx}\n{start} --> {end}\n{speaker}\n{text}\n")

    srt_content = "\n".join(srt_lines)  # 블록 사이에 빈 줄이 들어가도록 \n으로 join
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
    except Exception as e:
        print(f"[ERROR] Failed to write to {file_path}: {e}")

def remove_duplicate_start_times(samples):
    unique_samples = []
    seen_starts = set()
    for sample in samples:
        if sample[0] not in seen_starts:
            unique_samples.append(sample)
            seen_starts.add(sample[0])
    return unique_samples

def update_srt_dataset(start, end, speaker, original, translation):
    samples = parse_srt_files('downloads/transcription_refined.srt', 'downloads/translated.srt')

    if start or end or speaker or original or translation:
        new_sample = [start, end, speaker, original, translation]
        samples = [sample for sample in samples if sample[0] != start]
        samples.append(new_sample)

    # 시작 시간 기준으로 정렬.
    samples.sort(key=lambda sample: time_to_seconds(sample[0]))

    # transcription 파일에는 원본 텍스트(인덱스 3), translated 파일에는 번역 텍스트(인덱스 4) 사용
    write_srt_file('downloads/transcription_refined.srt', samples, text_index=3)
    write_srt_file('downloads/translated.srt', samples, text_index=4)

    new_dataset = gr.Dataset(samples=samples)

    # 텍스트박스 초기화와 함께 새 Dataset 반환.
    return new_dataset, "", "", "", "", ""