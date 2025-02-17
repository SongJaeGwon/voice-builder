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