from video_processing import json, openai, get_file_path
from config import OPEN_AI_TOKEN

openai.api_key = OPEN_AI_TOKEN

def transcribe_audio_whisper(audio_file, model="whisper-1"):
    client = openai.OpenAI(api_key=OPEN_AI_TOKEN)

    # 🔹 OpenAI Whisper API 요청
    with open(audio_file, "rb") as file:
        response = client.audio.transcriptions.create(
            model=model,
            file=file,
            response_format="verbose_json",
        )

    response_json = response.model_dump()
    output_path = get_file_path("transcription_whisper.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(response_json, f, indent=4, ensure_ascii=False)

    return response_json