import os
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
DEEPL_API_URL = os.getenv("API_URL")
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
OPEN_AI_TOKEN = os.getenv("OPEN_AI_TOKEN")