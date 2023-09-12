import io
import logging
import os

from google.cloud import texttospeech
from google.oauth2 import service_account
from gtts import gTTS
import openai
from pydub import AudioSegment
import speech_recognition as sr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

recognizer = sr.Recognizer()

# Create a client for the Google Text-to-Speech API
credentials_path = os.path.expanduser('./ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
text_to_speech_client = texttospeech.TextToSpeechClient(credentials=credentials)

def speech_to_text_google(wav_bytes:bytes) -> (str, Exception):
    try:
        audio_source = sr.AudioData(wav_bytes, 44100, 2)
        # using google speech recognition
        text = recognizer.recognize_google(audio_source)
        logger.info(f"wav is transcribed to {text} with google API")
        return (text, None)
    except Exception as e:
        logger.error(f"error when trying to recognize_google: {e}")
        return ("", e)

class NamedBytesIO(io.BytesIO):
    def __init__(self, buffer, name=None):
        super().__init__(buffer)
        self.name = name

def speech_to_text_whisper(wav_bytes:bytes) -> (str, Exception):
    try:
        audio_buffer = NamedBytesIO(wav_bytes, name="audio.wav")
        transcript = openai.Audio.transcribe("whisper-1", audio_buffer)
        text = transcript['text']
        logger.info(f"wav is transcribed to {text} with whisper")
        return (text, None)
    except Exception as e:
        logger.error(f"error when trying to call whisper: {e}")
        return ("", e)

def convert_mp3_to_wav(mp3_bytes: bytes) -> bytes:
    seg = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    wav_io = io.BytesIO()
    seg.export(wav_io, format="wav")
    return wav_io.getvalue()

def text_to_speech_google_translate(text:str) -> bytes:
    tts = gTTS(text=text, lang="en")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    mp3_bytes = fp.read()
    wav_bytes = convert_mp3_to_wav(mp3_bytes)
    return wav_bytes

def text_to_speech_gcp(text:str, name, ssml_gender) -> bytes:
    # if gender.lower() == "male":
    #     name = "en-US-News-M"
    #     ssml_gender = texttospeech.SsmlVoiceGender.MALE
    # elif gender.lower() == "female":
    #     name="en-US-News-K"
    #     ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    # else:
    #     return (None, "invalid gender, male/female")

    # Build the voice and audio config for the Text-to-Speech API request
    voice = texttospeech.VoiceSelectionParams(
        # language_code="cmn-CN",
        language_code="en-US",
        # name="cmn-TW-Wavenet-A",
        name=name,
        ssml_gender=ssml_gender
        # name="en-US-News-K",
        # ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
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

def tweak_sound(audio_bytes:bytes, octaves:float) -> bytes:
    # Create a stream from the bytes
    audio_stream = io.BytesIO(audio_bytes)
    # # Load the audio from the stream
    voice = AudioSegment.from_file(audio_stream, format="wav")
    new_sample_rate = int(voice.frame_rate * (2.0 ** octaves))

    # keep the same samples but tell the computer they ought to be played at the 
    # new, higher sample rate. This file sounds like a chipmunk but has a weird sample rate.
    hipitch_sound = voice._spawn(voice.raw_data, overrides={'frame_rate': new_sample_rate})

    # now we just convert it to a common sample rate (44.1k - standard audio CD) to 
    # make sure it works in regular audio players. Other than potentially losing audio quality (if
    # you set it too low - 44.1k is plenty) this should now noticeable change how the audio sounds.
    hipitch_sound = hipitch_sound.set_frame_rate(44100)
    # Export the modified voice as bytes
    # Create an AudioSegment from raw audio data
    audio_segment = AudioSegment(
        data=hipitch_sound.raw_data,
        sample_width=hipitch_sound.sample_width,
        frame_rate=hipitch_sound.frame_rate,
        channels=hipitch_sound.channels
    )

    # Export the audio as WAV format bytes
    return audio_segment.export(format="wav").read() 
