# __init__.py
import os
import re
import json
import yt_dlp
import openai
import subprocess
import requests
from pydub import AudioSegment
from elevenlabs.client import ElevenLabs
from .file_manager import get_file_path
from .srt_utils import parse_srt