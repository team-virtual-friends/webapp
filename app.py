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

openai.api_key = "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"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# socketio = SocketIO(app, cors_allowed_origins="*")
sock = Sock(app)

recognizer = sr.Recognizer()

API_KEY = "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"
API_URL = 'https://api.openai.com/v1/chat/completions'

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
}

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
        max_tokens=150
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
        sock.send(data)

def get_json(received) -> dict:
    try:
        json_object = json.loads(received)
        return json_object
    except ValueError as e:
        return {}

def base64_decode(raw):
    base64_bytes = raw.encode('ascii')
    return base64.b64decode(base64_bytes).decode('ascii')

def speech2text(json_object) -> str:
    wav_base64 = json_object['wav_base64']
    wav_bytes = base64_decode(wav_base64)
    try:
        # using google speech recognition
        text = recognizer.recognize_google(wav_bytes)
        return text
    except Exception as e:
        return ""

def wrap_response(data, message, err) -> str:
    resp = {}
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
        print(json_object)
        if not 'action' in json_object:
            ws.send(wrap_response(None, None, "unknown action"))
            continue
        
        action = json_object['action']
        if action == 'hello':
            ws.send(wrap_response(None, "hello there", None))
        if action == 'speech2text':
            text = speech2text(json_object)
            ws.send(wrap_response(None, text, None))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
