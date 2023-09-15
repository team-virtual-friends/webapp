import json
import logging
import requests
from typing import Iterator

import openai
from openai import ChatCompletion

from . import prompts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

openai.api_key = "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"
openai_api_url = 'https://api.openai.com/v1/chat/completions'

auth_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {openai.api_key}'
}

from requests.exceptions import Timeout

def infer_action(text, timeout_seconds=2):
    payload = {
        'messages': [
            {"role": "system", "content": "You are a helpful assistant that identifies the asked action in the input text. The output should be either 1. no action 2. dance 3. sit 4. stand. Only output one of the above 4 strings. Example: Text: can you dance? OUTPUT: dance"},
            {"role": "user", "content": f'Detect the asked action of the following text: {text}'}
        ],
        'model': "gpt-3.5-turbo",
    }

    try:
        response = requests.post(openai_api_url, headers=auth_headers, data=json.dumps(payload), timeout=timeout_seconds)
        response.raise_for_status()
        response_data = response.json()
        result = response_data['choices'][0]['message']['content']
        logger.info(result)
        return result
    except requests.exceptions.Timeout:
        logger.error("infer_action API call to OpenAI timed out")
        return "no action"

def infer_sentiment(text, timeout_seconds=2):
    payload = {
        'messages': [
            {"role": "system", "content": "You are a helpful assistant that identifies the sentiment of the input text. The output should be either 1. happy 2. neutral 3. sad 4. angry. Only output one of the above 4 strings. Example: Text: hahahah Output: happy"},
            {"role": "user", "content": f'Detect the sentiment of the input text: {text}'}
        ],
        'model': "gpt-3.5-turbo",
    }

    try:
        response = requests.post(openai_api_url, headers=auth_headers, data=json.dumps(payload), timeout=timeout_seconds)
        response.raise_for_status()
        response_data = response.json()
        result = response_data['choices'][0]['message']['content']
        logger.info(result)
        return result
    except requests.exceptions.Timeout:
        logger.error("infer_sentiment API call to OpenAI timed out")
        return "neutral"

# chronical_messages should be a list of dict; each dict should contain "role" and "content".
def infer_reply(chronical_messages:list, character_name:str) -> str:
    chronical_messages.append({"role": "system", "content": prompts.character_prompts[character_name]})
    reply = ChatCompletion.create(
        # model="gpt-3.5-turbo",
        model="gpt-4",
        messages=chronical_messages,
        max_tokens=100
    )
    # TODO: explore other index.
    return reply.choices[0].message.content

def stream_infer_reply(chronical_messages:list, character_name:str, custom_prompts:str) -> Iterator:
    # logger.info("start gpt infer")

    #   Testing new api for now.
    #     chronical_messages.append({"role": "system", "content": prompts.character_prompts[character_name]})
    #     return ChatCompletion.create(
    #         model="gpt-3.5-turbo",
    #         messages=chronical_messages,
    #         max_tokens=100,
    #         stream=True
    #     )

    full_prompt = process_messages(chronical_messages)
    base_prompt = prompts.character_prompts.get(character_name)
    if base_prompt is None:
        base_prompt = "You are an AI assistant created by Virtual Friends Team."
    if custom_prompts:
        full_prompt = custom_prompts + '\n' + full_prompt + "\nA:"
    else:
        full_prompt = base_prompt + '\n' + full_prompt + "\nA:"

    logger.info(full_prompt)
    return openai.Completion.create(
        model="text-davinci-003",
        prompt=full_prompt,
        max_tokens=100,
        temperature=1,
        stream=True
    )

def process_messages(messages):
    current_role = None
    combined_content = ""
    result = []

    for message in messages:
        # If the role changed or we reached the end
        if current_role and current_role != message["role"]:
            result.append(f"{current_role}: {combined_content.strip()}")
            combined_content = ""

        # If there's already content for this role, add a period before the new content
        separator = ". " if combined_content else ""
        combined_content += separator + message["content"]
        current_role = message["role"]

    # Handle the last message(s)
    if combined_content:
        result.append(f"{current_role}: {combined_content.strip()}")

    return "\n".join(result).replace("assistant:", "A:")

# This is for old ChatCompletion api.
# def get_content_from_chunk(chunk) -> str:
#     return chunk["choices"][0].get("delta", {}).get("content")

def get_content_from_chunk(chunk) -> str:
    return chunk['choices'][0]['text']