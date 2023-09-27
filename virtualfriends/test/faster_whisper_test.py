
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

from faster_whisper import WhisperModel


#
# https://github.com/guillaumekln/faster-whisper
#


import time

import io

import speech_recognition
import speech_recognition as sr
recognizer = sr.Recognizer()



# Path to your service account key file
credentials_path = '../ysong-chat-845e43a6c55b.json'
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

    # try:
    #     text = recognizer.recognize_google(audio_source)
    #     print(f"wav is transcribed to {text}")
    #
    # except sr.UnknownValueError:
    #     print("Google Web Speech API could not understand audio")
    # except sr.RequestError as e:
    #     print(f"Could not request results from Google Web Speech API; {e}")




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



    #
    #
    # audio_buffer = NamedBytesIO(wav_bytes, name="audio.wav")
    #
    # # model_size = "large-v2"
    # model_size = "tiny"
    # # Run on GPU with FP16
    # # model = WhisperModel(model_size, device="cuda", compute_type="float16")
    # # or run on GPU with INT8
    # # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
    # # or run on CPU with INT8
    # model = WhisperModel(model_size, device="cpu", compute_type="int8")
    #
    # start_time = time.time()
    # segments, info = model.transcribe(audio_buffer, beam_size=5)
    # end_time = time.time()
    # latency = end_time - start_time
    # print(f"faster whisper took {latency:.5f} seconds")
    #
    #
    # print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    # for segment in segments:
    #     print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))



def faster_whisper(wav_bytes, model_size="base", compute_type="int8"):
    # Create a NamedBytesIO object from WAV bytes
    audio_buffer = NamedBytesIO(wav_bytes, name="audio.wav")

    # Initialize the Whisper ASR model
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)

    # Transcribe the audio
    start_time = time.time()
    segments, info = model.transcribe(audio_buffer, beam_size=5)
    end_time = time.time()
    latency = end_time - start_time

    print(f"faster whisper took {latency:.5f} seconds")
    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    transcribed_segments = []
    for segment in segments:
        transcribed_segments.append([segment.start, segment.end, segment.text])

    return transcribed_segments


def main():
    # Get the user's text input
    # text = input("Please enter the text you'd like to convert to speech: ")

    text = "hi, 我叫宋毅。 大家好。 "
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

    start_time = time.time()
    whisper_speech2text(json_object)
    end_time = time.time()
    latency = end_time - start_time
    print(f"whisper took {latency:.5f} seconds")


    wav_base64 = json_object['data']
    wav_bytes = base64.b64decode(wav_base64)

    faster_whisper(wav_bytes)

    print("Done!")

if __name__ == '__main__':
    main()


