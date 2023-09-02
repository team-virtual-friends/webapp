from io import BytesIO
import logging
import os

from google.cloud import texttospeech
from google.oauth2 import service_account
from gtts import gTTS
import openai
from pydub import AudioSegment
import speech_recognition as sr

from custom_error import CustomError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

recognizer = sr.Recognizer()

# Create a client for the Google Text-to-Speech API
credentials_path = os.path.expanduser('./ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
text_to_speech_client = texttospeech.TextToSpeechClient(credentials=credentials)

def speech_to_text_google(wav_bytes:bytes) -> (str, CustomError):
    try:
        audio_source = sr.AudioData(wav_bytes, 44100, 2)
        # using google speech recognition
        text = recognizer.recognize_google(audio_source)
        logger.info(f"wav is transcribed to {text} with google API")
        return (text, CustomError.NoError())
    except Exception as e:
        logger.error(f"error when trying to recognize_google: {e}")
        return ("", CustomError(e))

# class NamedBytesIO(io.BytesIO):
#     def __init__(self, buffer, name=None):
#         super().__init__(buffer)
#         self.name = name

def speech_to_text_whisper(wav_bytes:bytes) -> (str, CustomError):
    try:
        audio_buffer = BytesIO(wav_bytes)
        transcript = openai.Audio.transcribe("whisper-1", audio_buffer)
        text = transcript['text']
        logger.info(f"wav is transcribed to {text} with whisper")
        return (text, CustomError.NoError())
    except Exception as e:
        logger.error(f"error when trying to call whisper: {e}")
        return ("", CustomError(e))

def convert_mp3_to_wav(mp3_bytes: bytes) -> bytes:
    seg = AudioSegment.from_mp3(BytesIO(mp3_bytes))
    wav_io = BytesIO()
    seg.export(wav_io, format="wav")
    return wav_io.getvalue()

def text_to_speech_google_translate(text:str) -> bytes:
    tts = gTTS(text=text, lang="en")
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    mp3_bytes = fp.read()
    wav_bytes = convert_mp3_to_wav(mp3_bytes)
    return wav_bytes

def text_to_speech_gcp(text:str) -> bytes:
    # Build the voice and audio config for the Text-to-Speech API request
    voice = texttospeech.VoiceSelectionParams(
        language_code="cmn-CN",
        name="cmn-TW-Wavenet-A",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        # Male voice
        # name = "cmn-TW-Standard-C",
        # ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        #        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.3  # Modify this value to adjust speech speed
    )
    # Perform the Text-to-Speech API request
    response = text_to_speech_client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=voice,
        audio_config=audio_config
    )
    return response.audio_content
