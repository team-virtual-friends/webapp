import json
import logging
import requests
from typing import Iterator

import openai
from openai import ChatCompletion

from . import prompts

# For log chat history in BQ.
from google.cloud import bigquery
import os
from google.oauth2 import service_account
from datetime import datetime
import asyncio

# Load the BigQuery credentials and create a BigQuery client
credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
print(credentials_path)

credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = bigquery.Client(credentials=credentials)

# Define your dataset and table names
dataset_name = 'virtualfriends'
table_name = 'chat_history'


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

openai.api_key = "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"
openai_api_url = 'https://api.openai.com/v1/chat/completions'

auth_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {openai.api_key}'
}

from requests.exceptions import Timeout

def infer_action(text, timeout_seconds=1):
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
        # logger.info(result)
        return result
    except requests.exceptions.Timeout:
        logger.error("infer_action API call to OpenAI timed out")
        return "no action"

def infer_sentiment(text, timeout_seconds=1):
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
        # logger.info(result)
        return result
    except requests.exceptions.Timeout:
        logger.error("infer_sentiment API call to OpenAI timed out")
        return "neutral"

async def log_chat_history(user_id, user_ip, character_id, chat_history, timestamp):
    try:
        # Create a reference to your dataset and table
        dataset_ref = client.dataset(dataset_name)
        table_ref = dataset_ref.table(table_name)
        table = client.get_table(table_ref)

        # Insert a new row into the table
        row_to_insert = (user_id, user_ip, character_id, chat_history, timestamp)

        client.insert_rows(table, [row_to_insert])

        logger.info("Log chat history data successfully")

    except Exception as e:
        logger.info(f"An error occurred when logging chat history: {e}")


def stream_infer_reply(chronical_messages:list, character_name:str, base_prompts:str, custom_prompts:str, user_ip:str) -> Iterator:
    # logger.info("start gpt infer")

    #   Testing new api for now.
    #     chronical_messages.append({"role": "system", "content": prompts.character_prompts[character_name]})
    #     return ChatCompletion.create(
    #         model="gpt-3.5-turbo",
    #         messages=chronical_messages,
    #         max_tokens=100,
    #         stream=True
    #     )

    full_prompts = process_messages(chronical_messages)

    env = os.environ.get('ENV', 'LOCAL')
    if env != 'LOCAL':
        # log chat history
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        loop = asyncio.new_event_loop()
        # Run the asynchronous function concurrently
        asyncio.set_event_loop(loop)
        loop.run_until_complete(log_chat_history("dummy", user_ip, character_name, full_prompts, current_timestamp))
        # Close the event loop
        loop.close()

    if custom_prompts is not None and len(custom_prompts) > 0:
        full_prompts = f"{custom_prompts}\n{full_prompts}\nA:"
    elif base_prompts is not None and len(base_prompts) > 0:
        full_prompts = f"{base_prompts}\n{full_prompts}\nA:"
    else:
        full_prompts = f"You are an AI assistant created by Virtual Friends Team.\n{full_prompts}\nA:"

    return openai.Completion.create(
        model="text-davinci-003",
        prompt=full_prompts,
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