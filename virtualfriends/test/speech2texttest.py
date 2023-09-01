
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
recognizer = sr.Recognizer()



# Path to your service account key file
credentials_path = '~/openai/text2speech/ysong-chat-845e43a6c55b.json'
credentials_path = os.path.expanduser(credentials_path)  # This line expands the '~'

# Create a client for the Google Text-to-Speech API
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = texttospeech.TextToSpeechClient(credentials=credentials)



class NamedBytesIO(io.BytesIO):
    def __init__(self, buffer, name=None):
        super().__init__(buffer)
        self.name = name


def convert_text_to_speech(text):
    # Build the voice and audio config for the Text-to-Speech API request
    voice = texttospeech.VoiceSelectionParams(
        language_code="cmn-CN",
        name="cmn-TW-Wavenet-A",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,  # Change this line
#        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.3  # Modify this value to adjust speech speed
    )

    # Perform the Text-to-Speech API request
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=voice,
        audio_config=audio_config
    )

    play_audio_from_bytes(response.audio_content)
    return str(base64.b64encode(response.audio_content))



def play_audio_from_bytes(audio_bytes):
    audio_segment = AudioSegment.from_wav(BytesIO(audio_bytes))
    play(audio_segment)


def convert_wav_to_compatible_format(input_wav_bytes):
    # Load the WAV data from bytes
    audio = AudioSegment.from_wav(io.BytesIO(input_wav_bytes))

    # Convert audio to desired format (44.1kHz sample rate and 16-bit sample width)
    audio = audio.set_frame_rate(44100).set_sample_width(2)

    # Convert the modified audio back to bytes
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")

    return buffer.getvalue()



def speech2text(json_object):
    wav_base64 = json_object['data']
    wav_bytes = base64.b64decode(wav_base64)

    wav_bytes = convert_wav_to_compatible_format(wav_bytes)
    play_audio_from_bytes(wav_bytes)

    audio_source = sr.AudioData(wav_bytes, 44100, 2)
    # using google speech recognition

    try:
        text = recognizer.recognize_google(audio_source)
        print(f"wav is transcribed to {text}")

    except sr.UnknownValueError:
        print("Google Web Speech API could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Web Speech API; {e}")


def whisper_speech2text(json_object) -> (str, str):

    wav_base64 = json_object['data']
    wav_bytes = base64.b64decode(wav_base64)
    try:
        audio_buffer = NamedBytesIO(wav_bytes, name="audio.wav")
        transcript = openai.Audio.transcribe("whisper-1", audio_buffer)
        text = transcript['text']

        print(text)
        # audio_source = sr.AudioData(wav_bytes, 44100, 2)
        # # using google speech recognition
        # text = recognizer.recognize_google(audio_source)
        # logger.info(f"wav is transcribed to {text}")
        return (text, "")
    except Exception as e:
        print(f"error when trying to call whisper: {e}")
        return ("", str(e))




def main():
    # Get the user's text input
    # text = input("Please enter the text you'd like to convert to speech: ")

    text = "你好 我叫zero"
    # Convert the provided text to speech

    start_time = time.time()
    audio = convert_text_to_speech(text)
    end_time = time.time()
    latency = end_time - start_time
    print(f"Execution took {latency:.5f} seconds")

    audio = audio[2:-1]

    json_object = {
        "data": audio
    }

    speech2text(json_object)
    whisper_speech2text(json_object)

    print("Done!")

if __name__ == '__main__':
    main()
