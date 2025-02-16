import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

def get_voice_list():
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    response = client.voices.get_all()
    voices = response.voices

    return {voice.voice_id: voice.name for voice in voices}
    # return [voice.name for voice in voices]

def get_voice_ids():
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    response = client.voices.get_all()
    voices = response.voices

    return [voice.voice_id for voice in voices]

def selected_upload_method(tab_id):
    """
    Return the ID (or label) of the selected tab
    so we can store it in Gradio state.
    """
    return tab_id