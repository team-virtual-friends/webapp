import requests

url = "https://api.elevenlabs.io/v1/voices"

api_key = "4fb91ffd3e3e3cd35cbf2d19a64fd4e9"

headers = {
  "Accept": "application/json",
    "xi-api-key": api_key
}

response = requests.get(url, headers=headers)

print(response.text)


#
#
#
#
# # Note: you need to be using OpenAI Python v0.27.0 for the code below to work
# import openai
# openai.api_key = "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"
#
# # audio_file= open("/Users/yisong/Desktop/valerie-0.m4a", "rb")
# audio_file= open("/Users/yisong/Desktop/valerie-voice-2.m4a", "rb")
#
#
# transcript = openai.Audio.transcribe("whisper-1", audio_file)
# print(transcript)