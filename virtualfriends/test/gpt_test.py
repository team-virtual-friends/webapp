import requests
import openai
from openai import ChatCompletion
import json


openai.api_key = "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"
openai_api_url = 'https://api.openai.com/v1/chat/completions'
auth_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {openai.api_key}'
}

def infer_action(text, timeout_seconds=3):
    payload = {
        'messages': [
            {"role": "system", "content": """
You are a helpful assistant that identifies the asked action in the input text.
The output should be one of no_action, dance, get_angry, laugh, clap, charm, make_heart, surprise, blow_kiss, backflip, cry, jump, spin.
Only output one of the above strings. Example: Text: can you dance? OUTPUT: dance
             """},
            {"role": "user", "content": f'Detect the asked action of the following text: {text}'}
        ],
        'model': "gpt-3.5-turbo",
    }

    # try:
    response = requests.post(openai_api_url, headers=auth_headers, data=json.dumps(payload), timeout=timeout_seconds)
    response.raise_for_status()
    response_data = response.json()
    result = response_data['choices'][0]['message']['content']
    # logger.info(result)
    return result
    # except requests.exceptions.Timeout:
    #     logger.error("infer_action API call to OpenAI timed out")
    #     return "no action"


# List of test inputs
test_inputs = [
    "Can you laugh?",
    "Show me a dance.",
    "Will you get angry?",
    "Is it possible for you to jump?",
    "How about a backflip?",
    "Can you clap?",
    "Do a spin for me."
]

# Iterating over test inputs and printing results
for text_input in test_inputs:
    print(f'Input: {text_input}')
    print(f'Action: {infer_action(text_input)}')
    print('-' * 50)