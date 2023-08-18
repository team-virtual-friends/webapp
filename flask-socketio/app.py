from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import requests
import json

from openai import ChatCompletion
import openai
# import logging

openai.api_key = "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"


app = Flask(__name__)
socketio = SocketIO(app)

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


@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('chat_message')
def handle_chat_message(data):
    user_input = data['user_input']
    messages = data.get('messages', [])

    if not user_input:
        emit('error', {'error': 'User input is missing'}, broadcast=False)
        return

    messages.append({"role": "user", "content": user_input})
    chat_response = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=150
    )
    assistant_response = chat_response.choices[0].message.content
    messages.append({"role": "system", "content": assistant_response})

    action = detect_action(assistant_response)
    sentiment = detect_sentiment(assistant_response)

    emit('chat_response', {
        "assistant_response": assistant_response,
        "action": action,
        "sentiment": sentiment,
        "messages": messages
    })

if __name__ == '__main__':
    socketio.run(app, port=5011)
