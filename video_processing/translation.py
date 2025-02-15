from video_processing import requests
from config import DEEPL_API_KEY, DEEPL_API_URL

def translate_srt(input_srt, output_srt, source_lang, target_lang):
    with open(input_srt, "r", encoding="utf-8") as f:
        lines = f.readlines()
    translated_lines = []
    for line in lines:
        if "-->" in line or line.strip().isdigit() or line.strip() == "":
            translated_lines.append(line)
        else:
            translated_text = translate_text(line.strip(), source_lang, target_lang)
            translated_lines.append(translated_text + "\n")
    with open(output_srt, "w", encoding="utf-8") as f:
        f.writelines(translated_lines)
    return output_srt

def translate_text(text, source_lang, target_lang):
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"}
    data = {
        "text": [text],
        "source_lang": source_lang.upper(),
        "target_lang": target_lang.upper()
    }
    response = requests.post(DEEPL_API_URL, headers=headers, data=data)
    if response.status_code == 200:
        result = response.json()
        return result["translations"][0]["text"]
    else:
        print("❌ 번역 실패:", response.text)
        return text