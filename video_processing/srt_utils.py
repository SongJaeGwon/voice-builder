from video_processing import re, get_file_path

def create_srt(transcription):
    if "segments" not in transcription:
        print("⚠️ 변환된 자막 데이터가 없습니다.")
        return
    
    output_path = get_file_path("transcription.srt")

    with open(output_path, "w", encoding="utf-8") as f:
        for idx, segment in enumerate(transcription["segments"]):
            start_time = seconds_to_srt_time(segment["start"])
            end_time = seconds_to_srt_time(segment["end"])
            text = segment["text"].strip()
            f.write(f"{idx+1}\n{start_time} --> {end_time}\n{text}\n\n")
    return output_path

def seconds_to_srt_time(seconds):
    millisec = int((seconds % 1) * 1000)
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

def parse_srt(srt_file):
    srt_pattern = re.compile(r"(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]*?)(?=\n\d+\s*\n|\Z)")
    with open(srt_file, "r", encoding="utf-8") as file:
        content = file.read()
    matches = srt_pattern.findall(content)
    subtitles = []
    for _, start, end, text in matches:
        start_seconds = srt_time_to_seconds(start)
        end_seconds = srt_time_to_seconds(end)
        text = text.strip().replace("\n", " ")
        subtitles.append({"start": start_seconds, "end": end_seconds, "text": text})
    return subtitles

def srt_time_to_seconds(time_str):
    hours, minutes, sec_millis = time_str.split(":")
    seconds, millis = map(int, sec_millis.split(","))
    return int(hours) * 3600 + int(minutes) * 60 + seconds + millis / 1000