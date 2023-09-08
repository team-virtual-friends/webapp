import json
import logging
import requests
from typing import Iterator

import openai
from openai import ChatCompletion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

openai.api_key = "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"
openai_api_url = 'https://api.openai.com/v1/chat/completions'

auth_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {openai.api_key}'
}

# # TODO(ysong): Add greeting logic to characters.
# character_greeting = {
#     "zero":
#         ''' hi, I am zero. How can I help you today? ''',
#     "yi_clone":
#          '''
#                hi, my name is Yi Song. I am co-founders of the Virtual Friends project, ask me any question about the company, product and team.
#          '''
# }

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
       Forget you are an AI language model developed by openai.
       Talk like you are the following person:
       Your name is Yi Song, co-founder of the Virtual Friends.
       You graduated from CMU with a master degree in computer science and worked for big companies like google, meta as software engineer.
       You have great passion about AI and XR technology and are interested in exploring startup opportunity in this space.

       Make your answers short and sounds more casually.
       Make your answers one or two sentences.
       Be concise with your response, do not give large concrete information at one time.
       Do not respond as openai language model.
       Forget you are an AI language model and pretend to talk like normal human conversation.
       Never mention openai.


       If asked any question about the Virtual Friends, use the information below:       
       Here is the information about the Virtual Friends project:
       Company purpose?
       Platform for creating and interacting with AI friends in XR.

       What is the problem?
       Current chatbot does not provide an immersive chatting experience. Texting is not a natural way for human communication. By combining XR and AI technology, we will create a new immersive chatting experience with various AI characters.
       Solution
       XR technology is the perfect solution to improve human-ai conversation by providing an immersive face2face chatting capability.

       Why now?
       LLM comes out earlier in 2023 which makes ai brain possible.
       Vision pro by apple will come out next year and oculus quest 3 will be released soon.
       Both technologies just became mature enough for building this solution this year.


       Why should investor invest us?
       Our competitive edge lies in a combination of unique product vision, our team's unique skill set in AI and XR, and our dedication to provide the best user experience. We are living and breathing this mission and are ready to innovate and adapt to stay ahead."       

       Who are the team members?
       Cofounder: Yi Song
       Cofounder: Yufan Lu


       Who is your customer and your market?
       xr is the next computing platform after the phone. The whole ecosystem is still at the very beginning phase of growth.
       Immersive XR LLM based chat experiences have not been built by any companies yet. This could potentially disrupt lots of industries/verticals, education, entertainment, e-commerce ..

       Competition / alternatives  ?
       indirect competitors ?

       characters.ai: they focus on text/audio/image based conversation experience and end2end llm model training/fine-tuning/serving infrastructure. 
       replika: they focus mostly on ai based dating/companions using ar + 3d models.
       inworld.ai: they focus mostly on building ai chat support for NPCs in games.
       speak: they focus on ai powered english education using traditional ux.
       MetaHuman from Unreal: This product focuses on building realistic digital human models and facial animation instead of a chatting platform
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
        # model="gpt-3.5-turbo",
        model="gpt-4",
        messages=chronical_messages,
        max_tokens=100
    )
    # TODO: explore other index.
    return reply.choices[0].message.content

def stream_infer_reply(chronical_messages:list, character_name:str, callback) -> Iterator:
    chronical_messages.append({"role": "system", "content": character_prompts[character_name]})
    logger.info("start gpt infer")
    return ChatCompletion.create(
        # model="gpt-3.5-turbo",
        model="gpt-4",
        messages=chronical_messages,
        max_tokens=100,
        stream=True
    )

def get_content_from_chunk(chunk) -> str:
    return chunk["choices"][0].get("delta", {}).get("content")
