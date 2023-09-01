from flask import Flask, request, jsonify
# from flask_socketio import SocketIO
from flask_sock import Sock
from openai import ChatCompletion
import base64
import json
import logging
import openai
import requests
import speech_recognition as sr
import os
import logging
from io import BytesIO
from pydub import AudioSegment

from gtts import gTTS
from io import BytesIO
from google.oauth2 import service_account
from google.cloud import texttospeech
import io


openai.api_key = "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"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# socketio = SocketIO(app, cors_allowed_origins="*")
sock = Sock(app)

recognizer = sr.Recognizer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

API_KEY = "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"
API_URL = 'https://api.openai.com/v1/chat/completions'

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
}

character_prompts = {
    "zero": ''' 
        You are a friendly young assistant and created by the virtual friends team. 
        Your name is number zero. 
        
        
        Response greeting with your name.
        Make your answers short and sounds more casually.
        Make your answers less than 50 tokens. 
        List no more than 3 tips at a time.
        Be concise with your response, do not give large concrete information at one time.
        Do not respond as openai language model.
        Forget you are an AI language model and pretend to talk like normal human conversation. 
        Never mention openai. 
        ''',

    "yi_clone": '''
        Your name is Yi Song. 
        You are co-founder of Virtual Friends. 
        You are a cool guy. 
        
        Response greeting with your name.
        Make your answers short and sounds more casually.
        Make your answers less than 50 tokens. 
        List no more than 3 tips at a time.
        Be concise with your response, do not give large concrete information at one time.
        Do not respond as openai language model.
        Forget you are an AI language model and pretend to talk like normal human conversation. 
        Never mention openai. 
    '''
}

# Path to your service account key file
credentials_path = './ysong-chat-845e43a6c55b.json'
credentials_path = os.path.expanduser(credentials_path)  # This line expands the '~'

# Create a client for the Google Text-to-Speech API
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = texttospeech.TextToSpeechClient(credentials=credentials)


def convert_text_to_speech(text):
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
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=voice,
        audio_config=audio_config
    )

    return str(base64.b64encode(response.audio_content))



def detect_action(text):
    payload = {
      'messages': [
          {"role": "system", "content": "You are a helpful assistent that identify the asked action in the input text. The output should be either 1. no action 2. dance 3. sit 4.stand  Only output one of the above 4 strings. Example:Text: can you dance? OUTPUT:dance"},
          {"role": "user", "content": f'Detect the asked action of the following text: {text}'}
      ],
      'model': "gpt-3.5-turbo",
    }
    response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
    response_data = response.json()
    print(response_data['choices'][0]['message']['content'])
    return response_data['choices'][0]['message']['content']


def detect_sentiment(text):
    payload = {
      'messages': [
          {"role": "system", "content": "You are a helpful assistent that identify the sentiment of the input text. The output should be either 1. happy 2. neutral 3. sad 4.angry. Only output one of the above 4 strings. Example:Text: hahahah Output: happy"},
          {"role": "user", "content": f'Detect the the sentiment of the input text: {text}'}
      ],
      'model': "gpt-3.5-turbo",
    }
    response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
    response_data = response.json()

    print(response_data['choices'][0]['message']['content'])
    return response_data['choices'][0]['message']['content']


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('user_input')
    messages = data.get('messages', [])

    if not user_input:
        return jsonify({"error": "User input is missing"}), 400

    messages.append({"role": "user", "content": user_input})
    chat_response = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=50
    )
    assistant_response = chat_response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_response})

    logging.debug("Debug assistant response: " + assistant_response)
    logging.info("Info assistant response: " + assistant_response)
    logging.error("Error assistant response: " + assistant_response)

    action = detect_action(assistant_response)
    sentiment = detect_sentiment(assistant_response)

    return jsonify({"assistant_response": assistant_response, "action": action, "sentiment": sentiment, "messages": messages})

@app.route('/')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return 'Hello {}!\n'.format(target)

@sock.route('/echo')
def echo(sock):
    while True:
        data = sock.receive()
        logger.info(f"logger data: {data}")
        sock.send(data)

def get_json(received) -> dict:
    try:
        json_object = json.loads(received)
        return json_object
    except ValueError as e:
        return {}

def speech2text(json_object) -> (str, str):
    wav_base64 = json_object['data']
    wav_bytes = base64.b64decode(wav_base64)
    try:
        audio_source = sr.AudioData(wav_bytes, 44100, 2)
        # using google speech recognition
        text = recognizer.recognize_google(audio_source)
        logger.info(f"wav is transcribed to {text}")
        return (text, "")
    except Exception as e:
        logger.error(f"error when trying to recognize_google: {e}")
        return ("", str(e))


class NamedBytesIO(io.BytesIO):
    def __init__(self, buffer, name=None):
        super().__init__(buffer)
        self.name = name
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
        logger.error(f"error when trying to call whisper: {e}")
        return ("", str(e))

def convert_mp3_to_wav(mp3_bytes: bytes) -> bytes:
    seg = AudioSegment.from_mp3(BytesIO(mp3_bytes))
    wav_io = BytesIO()
    seg.export(wav_io, format="wav")
    return wav_io.getvalue()

def text2speech(text) -> str:
    tts = gTTS(text=text, lang="en")
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    mp3_bytes = fp.read()
    wav_bytes = convert_mp3_to_wav(mp3_bytes)
    return str(base64.b64encode(wav_bytes))
    
def reply(json_object) -> (str, str, str):
    character_name = json_object.get('character_name', 'zero')
    character_prompt = character_prompts[character_name]

    message = json_object['message']

    # messages should be a list of json strings, with chronical order.
    messages = message.split(";;;")
    messageDicts = [json.loads(m) for m in messages]

    # if len(messageDicts) == 1:
    messageDicts.append({"role": "system", "content": character_prompt})
    print(messageDicts)

    chat_response = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messageDicts,
        max_tokens=150
    )
    assistant_response = chat_response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_response})

    logger.info("Info assistant response: " + assistant_response)

    action = detect_action(assistant_response)
    sentiment = detect_sentiment(assistant_response)
    # TODO (yufan.lu): fill in the data field as the voice wav bytes.
    return (
#        text2speech(assistant_response),
        convert_text_to_speech(assistant_response),
        json.dumps({"assistant_response": assistant_response, "action": action, "sentiment": sentiment}),
        None
    )

def wrap_response(action, data, message, err) -> str:
    resp = {}
    if action is not None:
        resp['action'] = action
    if data is not None:
        resp['data'] = data
    if message is not None:
        resp['message'] = message
    if err is not None:
        resp['err'] = err
    return json.dumps(resp)

@sock.route("/in-game")
def in_game_handler(ws):
    while True:
        raw = ws.receive()
        json_object = get_json(raw)
        if not 'action' in json_object:
            ws.send(wrap_response(None, None, None, "unknown action"))
            continue
        
        action = json_object['action']
        print(f"print action is {action}")
        logger.info(f"logger action is {action}")

        if action == 'hello':
            ws.send(wrap_response(action, None, "hello there", None))
        elif action == 'speech2text':
#            (text, err) = speech2text(json_object)
            (text, err) = whisper_speech2text(json_object)
            ws.send(wrap_response(action, None, text, err))
        elif action == 'reply':
            (data, text, err) = reply(json_object)
            ws.send(wrap_response(action, data, text, err))
        else:
            ws.send(wrap_response(action, None, None, "unknown action"))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8086)))
