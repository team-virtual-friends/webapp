from pydub import AudioSegment
from pydub.playback import play
import requests
import io
import time
from io import BytesIO
import logging

logger = logging.getLogger('gunicorn.error')

import base64
def convert_mp3_to_wav(mp3_bytes: bytes) -> bytes:
    seg = AudioSegment.from_mp3(BytesIO(mp3_bytes))
    wav_io = io.BytesIO()
    seg.export(wav_io, format="wav")
    return wav_io.getvalue()

#    voice_id = "sij1MJjyxTEZi1YPU3h1"

def text_to_audio(text, voice_id) -> bytes:
    api_key = "4fb91ffd3e3e3cd35cbf2d19a64fd4e9"
    url = "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id + "?optimize_streaming_latency=3"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.9,
            "similarity_boost": 0.9
        }
    }

    start_time = time.time()
    response = requests.post(url, json=data, headers=headers)
    end_time = time.time()
    latency = end_time - start_time

    logger.error(f"Voice Clone Latency: {latency}")

    wav = None
    if response.status_code == 200:
        logger.error(f"Request was successful. Status code: {response.status_code}" )
        mp3_content = response.content
        wav = convert_mp3_to_wav(mp3_content)

#        play_audio_from_bytes(wav)
    else:
        logger.error(f"Request failed. Status code: {response.status_code}" )

    # logger.error(f"wav: {wav}" )
    return wav


def play_audio_from_bytes(audio_bytes):
    audio_segment = AudioSegment.from_wav(BytesIO(audio_bytes))
    play(audio_segment)

# text = "Hello World， my name is Yi Song. I love AI and XR, I am always ready to build something new."
# text_to_audio(text)
