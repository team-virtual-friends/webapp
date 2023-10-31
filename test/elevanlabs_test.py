import requests

url = "https://api.elevenlabs.io/v1/voices/add"

api_key = "4fb91ffd3e3e3cd35cbf2d19a64fd4e9"

headers = {
  "Accept": "application/json",
  "xi-api-key": api_key
}

data = {
    'name': 'test0',
#    'labels': '{"accent": "American"}',
    'description': 'test audio'
}

files = [
    ('files', ('/Users/yisong/Desktop/valerie-0.m4a', open('/Users/yisong/Desktop/valerie-0.m4a', 'rb'), 'audio/mpeg')),
    # ('files', ('sample2.mp3', open('sample2.mp3', 'rb'), 'audio/mpeg'))
]

response = requests.post(url, headers=headers, data=data, files=files)
print(response.text)

