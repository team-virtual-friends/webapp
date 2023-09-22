from pydub import AudioSegment
from pydub.playback import play
import requests

import pyaudio

import io
from io import BytesIO



import os
from google.cloud import texttospeech
from pydub import AudioSegment
from google.oauth2 import service_account
from gtts import gTTS
from io import BytesIO
import base64
from pydub.playback import play
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO
import base64


import openai
openai.api_key = "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"


import time


import io

import speech_recognition
import speech_recognition as sr



import requests
from pydub import AudioSegment
import io


## voice id libarary
## https://api.elevenlabs.io/v1/voices
##

def convert_mp3_to_wav(mp3_bytes: bytes) -> bytes:
    seg = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    wav_io = io.BytesIO()
    seg.export(wav_io, format="wav")
    return wav_io.getvalue()


def text_to_audio(text):
    api_key = "4fb91ffd3e3e3cd35cbf2d19a64fd4e9"
    CHUNK_SIZE = 1024
    voice_id = "LcfcDJNUP1GQjkzn1xUU"
    url = "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id  # + "?optimize_streaming_latency=3"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }



    start_time = time.time()  # Record the start time
    response = requests.post(url, json=data, headers=headers)
    end_time = time.time()  # Record the end time
    latency = end_time - start_time  # Calculate the latency
    print("Latency1111:", latency)  # Print the latency

    if response.status_code == 200:
        print("Request was successful. Status code:", response.status_code)
        mp3_content = response.content

        start_time = time.time()  # Record the start time
        wav = convert_mp3_to_wav(mp3_content)
        end_time = time.time()  # Record the end time
        latency = end_time - start_time  # Calculate the latency
        print("Latency2222:", latency)  # Print the latency


        play_audio_from_bytes(wav)


    else:
        print("Request failed. Status code:", response.status_code)
        print("Response content:", response.text)




# Path to your service account key file
credentials_path = '../ysong-chat-845e43a6c55b.json'
credentials_path = os.path.expanduser(credentials_path)  # This line expands the '~'

# Create a client for the Google Text-to-Speech API
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = texttospeech.TextToSpeechClient(credentials=credentials)


def play_audio_from_bytes(audio_bytes):
    audio_segment = AudioSegment.from_wav(BytesIO(audio_bytes))
    play(audio_segment)

def convert_text_to_speech(text):
    # Build the voice and audio config for the Text-to-Speech API request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        #name="cmn-TW-Wavenet-A",
        name="en-US-News-K",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,  # Change this line
#        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.3  # Modify this value to adjust speech speed
    )



    start_time = time.time()  # Record the start time

    # Perform the Text-to-Speech API request
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=voice,
        audio_config=audio_config
    )


    end_time = time.time()  # Record the end time
    latency = end_time - start_time  # Calculate the latency
    print("Latency333:", latency)  # Print the latency



    play_audio_from_bytes(response.audio_content)
#    return str(base64.b64encode(response.audio_content))

# text = "Hi there, it is so nice to meet you. how are you doing"
text = "Hi there, what can i do for you today? mac price is 12345"

text_to_audio(text)


convert_text_to_speech(text)