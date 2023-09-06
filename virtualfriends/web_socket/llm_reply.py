import json
import logging
import requests
from typing import Iterator

import openai
from openai import ChatCompletion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

openai.api_key = "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"
openai_api_url = 'comp'

auth_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {openai.api_key}'
}

character_prompts = {
    "zero": ''' 
        You are a friendly young assistant and created by the virtual friends team. 
        Your name is number zero. 
        You try to make people happy and positive.
    
        When the user say hi, response hi with your name.
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
        
        When the user say hi, response hi with your name.
        Make your answers short and sounds more casually.
        Make your answers less than 50 tokens. 
        List no more than 3 tips at a time.
        Be concise with your response, do not give large concrete information at one time.
        Do not respond as openai language model.
        Forget you are an AI language model and pretend to talk like normal human conversation. 
        Never mention openai. 
    '''
}

def infer_action(text):
    payload = {
      'messages': [
          {"role": "system", "content": "You are a helpful assistent that identify the asked action in the input text. The output should be either 1. no action 2. dance 3. sit 4.stand  Only output one of the above 4 strings. Example:Text: can you dance? OUTPUT:dance"},
          {"role": "user", "content": f'Detect the asked action of the following text: {text}'}
      ],
      'model': "gpt-3.5-turbo",
    }
    response = requests.post(openai_api_url, headers=auth_headers, data=json.dumps(payload))
    response_data = response.json()
    logger.info(response_data['choices'][0]['message']['content'])
    return response_data['choices'][0]['message']['content']

def infer_sentiment(text):
    payload = {
      'messages': [
          {"role": "system", "content": "You are a helpful assistent that identify the sentiment of the input text. The output should be either 1. happy 2. neutral 3. sad 4.angry. Only output one of the above 4 strings. Example:Text: hahahah Output: happy"},
          {"role": "user", "content": f'Detect the the sentiment of the input text: {text}'}
      ],
      'model': "gpt-3.5-turbo",
    }
    response = requests.post(openai_api_url, headers=auth_headers, data=json.dumps(payload))
    response_data = response.json()

    logger.info(response_data['choices'][0]['message']['content'])
    return response_data['choices'][0]['message']['content']

# chronical_messages should be a list of dict; each dict should contain "role" and "content".
def infer_reply(chronical_messages:list, character_name:str) -> str:
    chronical_messages.append({"role": "system", "content": character_prompts[character_name]})
    reply = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chronical_messages,
        max_tokens=150
    )
    # TODO: explore other index.
    return reply.choices[0].message.content

def stream_infer_reply(chronical_messages:list, character_name:str, callback) -> Iterator:
    chronical_messages.append({"role": "system", "content": character_prompts[character_name]})
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": chronical_messages,
        "max_tokens": 300
        # other payload data
    }

    return ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chronical_messages,
        max_tokens=150,
        stream=True
    )

def get_content_from_chunk(chunk) -> str:
    return chunk["choices"][0].get("delta", {}).get("content")
