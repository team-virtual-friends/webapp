from pydub import AudioSegment
from pydub.playback import play
import requests

import pyaudio

import io
from io import BytesIO

import time


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
url = "https://api.elevenlabs.io/v1/voices"

api_key = "4fb91ffd3e3e3cd35cbf2d19a64fd4e9"
#
# headers = {
#   "Accept": "application/json",
#   "xi-api-key": api_key
# }
#
# response = requests.get(url, headers=headers)
#
# print(response.text)


voice_id = "sij1MJjyxTEZi1YPU3h1"

import asyncio
import websockets
import json
import base64

async def text_to_speech(voice_id):
    model = 'eleven_monolingual_v1'
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model}"

    async with websockets.connect(uri) as websocket:

        # Initialize the connection
        bos_message = {
            "text": " ",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": True
            },
            "xi_api_key": api_key,  # Replace with your API key
        }
        await websocket.send(json.dumps(bos_message))

        # Send "Hello World" input
        input_message = {
            "text": "Hello World， my name is Yi Song. ",
            "try_trigger_generation": True
        }

        start_time = time.time()  # Record the start time

        await websocket.send(json.dumps(input_message))

        # Send EOS message with an empty string instead of a single space
        # as mentioned in the documentation
        eos_message = {
            "text": ""
        }
        await websocket.send(json.dumps(eos_message))

        # Added a loop to handle server responses and print the data received
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                # print("Server response:", data)

                if data["audio"]:

                    end_time = time.time()  # Record the end time
                    latency = end_time - start_time  # Calculate the latency
                    print("Wss Latency:", latency)  # Print the latency


                  # Decode the Base64 data into binary audio data
                    audio_binary = base64.b64decode(data["audio"])

                    # Create an audio segment from the binary data
                    audio_segment = AudioSegment.from_mp3(BytesIO(audio_binary))

                    # Play the audio segment
                    play(audio_segment)

                    print("Received audio chunk")
                else:
                    print("No audio data in the response")
                    break
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break

asyncio.get_event_loop().run_until_complete(text_to_speech(voice_id))