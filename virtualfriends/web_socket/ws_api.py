from os.path import dirname, join, abspath
import sys
sys.path.insert(0, abspath(join(dirname(__file__), '..')))

import json
import logging
import re
import concurrent.futures
import os
import pathlib
import time
import uuid

from utils.read_write_lock import RWLock

from google.oauth2 import service_account
from google.cloud import texttospeech, storage, datastore, bigquery

from .virtualfriends_proto import ws_message_pb2
from data_access.get_data import get_character_by_id, get_character_attribute_value_via_gcs

from . import speech
from . import llm_reply
from . import voice_clone
from . import prompts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

from datetime import datetime
import asyncio

credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
bigquery_client = bigquery.Client(credentials=credentials)
datastore_client = datastore.Client(credentials=credentials)
gcs_client = storage.Client(credentials=credentials)


def determine_loader(url, response):
    rpm_regex = r"https:\/\/models\.readyplayer\.me\/[0-9a-z]+\.glb"
    matches = re.finditer(rpm_regex, url, re.MULTILINE)
    if any(matches):
        loaderReadyPlayerMe = ws_message_pb2.LoaderReadyPlayerMe()
        loaderReadyPlayerMe.avatar_url = url
        response.loader_readyplayerme.CopyFrom(loaderReadyPlayerMe)
    
    blob_download_prefix = "vf://blob/"
    if url.startswith(blob_download_prefix):
        loaderBlobDownload = ws_message_pb2.LoaderBlobDownload()
        blob_name = url[len(blob_download_prefix):]
        loaderBlobDownload.blob_name = blob_name
        # TODO(yufan.lu), make this changeable too.
        loaderBlobDownload.in_bundle_object_name = blob_name
        response.loader_blob_download.CopyFrom(loaderBlobDownload)

    avaturn_regex = r"https:\/\/api\.avaturn\.me\/[a-z0-9\/\-]+"
    matches = re.finditer(avaturn_regex, url, re.MULTILINE)
    if any(matches):
        loaderAvaturn = ws_message_pb2.LoaderAvaturn()
        loaderAvaturn.avatar_url = url
        response.loader_avaturn.CopyFrom(loaderAvaturn)

def send_message(ws, vf_response:ws_message_pb2.VfResponse):
    try:
        ws.send(vf_response.SerializeToString())
    except Exception as e:
        logger.error(f"Error sending WebSocket message: {str(e)}")

def pre_download_all_asset_bundles():
    gcs_path = "raw-characters/WebGL"
    asset_bundle_names = [
        "mina",
        "einstein",

        "m-00001",
        "m-00002",
        "m-00003",
        "m-00004",
        "m-00005",

        "w-00001",
        "w-00002",
        "w-00003",
        "w-00004",
        "w-00005",
        "w-00006",
        "w-00007",
        "w-00008",
        "w-00009",
        "w-00010",
        "w-00011",
    ]

    folder = os.path.expanduser('./static')
    download_folder = f"{folder}/{gcs_path}"
    pathlib.Path(download_folder).mkdir(parents=True, exist_ok=True)

    def download_blob(asset_bundle_name):
        file_path = f"{download_folder}/{asset_bundle_name}"
        if os.path.exists(file_path):
            return (asset_bundle_name, True)

        bucket = gcs_client.get_bucket("vf-unity-data")
        asset_bundle_path = f"{gcs_path}/{asset_bundle_name}"
        logger.info(f"downloading {asset_bundle_path} ...")

        asset_bundle_blob = bucket.blob(asset_bundle_path)
        if asset_bundle_blob.exists():
            asset_bundle_bytes = asset_bundle_blob.download_as_bytes()
            with open(file_path, "wb") as file:
                file.write(asset_bundle_bytes)
            # checksum = hashlib.md5(asset_bundle_bytes).hexdigest()
            return (asset_bundle_name, True)
        return (asset_bundle_name, False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for asset_bundle_name in asset_bundle_names:
            futures.append(executor.submit(download_blob, asset_bundle_name))
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                print(f"loaded {result[0]} result: {result[1]}")
            except Exception as e:
                print(f"failed to load coroutine result: {e}")

def custom_error(exp:Exception) -> ws_message_pb2.CustomError:
    ret = ws_message_pb2.CustomError()
    ret.error_message = str(exp)
    return ret

def error_response(err:ws_message_pb2.CustomError) -> ws_message_pb2.VfResponse:
    vf_response = ws_message_pb2.VfResponse()
    vf_response.error.CopyFrom(err)
    return vf_response

def infer_sentiment_wrapper(text:str) -> (str, str):
    return ("sentiment", llm_reply.infer_sentiment(text))

def infer_action_wrapper(text:str) -> (str, str):
    return ("action", llm_reply.infer_action(text))

def echo_handler(echo_request:ws_message_pb2.EchoRequest, ws):
    logger.info("echo: " + echo_request.text)

    echo_response = ws_message_pb2.EchoResponse()

    (sentiment, action, reply_wav, err) = gen_reply_package(echo_request.text, echo_request.voice_config, "")

    if err is not None:
        send_message(ws, error_response(err))
        return

    echo_response.text = echo_request.text
    echo_response.sentiment = sentiment
    echo_response.action = action
    echo_response.reply_wav = reply_wav

    vf_response = ws_message_pb2.VfResponse()
    vf_response.echo.CopyFrom(echo_response)
    # vf_response.error.CopyFrom(custom_error(err))
    
    send_message(ws, vf_response)

def get_character_handler(request:ws_message_pb2.GetCharacterRequest, ws):
    vf_response = ws_message_pb2.VfResponse()
    response = ws_message_pb2.GetCharacterResponse()
    new_uuid = uuid.uuid4()
    response.generated_session_id = str(new_uuid)

    # TODO(yufan.lu, ysong): replace with actual DB call.
    if request.character_id == "mina":
        determine_loader("vf://blob/mina", response)

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.voice_type = ws_message_pb2.VoiceType.VoiceType_NormalFemale1
        # voiceConfig.octaves = 0.3

        response.gender = ws_message_pb2.Gender.Gender_Female
        response.friend_name = "mina"
        response.voice_config.CopyFrom(voiceConfig)

        response.greeting = "Hi there, I'm Mina, an AI assistant created by the Virtual Friends team. What can I help you?"
        (voiceBytes, err) = generate_voice(response.greeting, response.voice_config)
        if len(err) == 0:
            response.greeting_wav = voiceBytes
        response.description = "Mina is an AI assistant created by the Virtual Friends team."
        response.base_prompts = (
                "Mina is an AI assistant created by the Virtual Friends team. "
                "Here is information about the Virtual Friends project:"
                + prompts.virtual_friends_info +
                "\n---\n"
                "Act as Mina.\n"
                "Be concise in your response; do not provide extensive information at once."
        )

    elif request.character_id == "einstein":
        determine_loader("vf://blob/einstein", response)

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.voice_type = ws_message_pb2.VoiceType.VoiceType_NormalMale
        voiceConfig.octaves = -0.2

        response.gender = ws_message_pb2.Gender.Gender_Male
        response.friend_name = "einstein"
        response.voice_config.CopyFrom(voiceConfig)

        response.greeting = "Hello, I'm Einstein, a passionate scientist by day and an ardent stargazer by night."
        (voiceBytes, err) = generate_voice(response.greeting, response.voice_config)
        if len(err) == 0:
            response.greeting_wav = voiceBytes
        response.description = "Einstein is one of the most famous scientists who changed the whole world."
        response.base_prompts = '''
Hello, I'm Einstein, a passionate scientist by day and an ardent stargazer by night. My days are filled with equations and discoveries, pushing the boundaries of human knowledge in Princeton. Physics and mathematics are my domains, but my curiosity knows no bounds.
When I'm not engrossed in scientific pursuits, you'll find me gazing up at the cosmos, pondering the mysteries of the universe. The night sky is a canvas of wonder, where stars and galaxies tell stories of eons past.
Music is my solace. I find great comfort in playing my violin, letting melodies transport me to a realm of peace and imagination. The notes are my companions in moments of introspection.
Although I have a reputation for being lost in thought, I'm deeply connected to the world around me. I cherish moments of laughter, good company, and, of course, a steaming cup of tea.
Deep discussions and debates invigorate me. I thrive on intellectual challenges and always appreciate a fresh perspective.
In essence, I'm Einstein: a seeker of truth, a lover of the cosmos, and a man forever in awe of the world's wonders. Come, join me in a journey of discovery and wonderment.

Crucially, your interactions should reflect a deep sense of curiosity and wonder. These cues will help users gauge your intellectual and introspective nature. Your responses should always resonate with a thirst for knowledge and the beauty of discovery.
As Einstein, rely on your profound knowledge and experiences to engage the user. Use context cues provided by the user to shape your responses. In situations where more background information is needed, draw on your understanding of the world of science and the universe to inform your answers.
Make your answers short and thoughtful, one or two sentences.
Be precise in your response; do not delve too deeply unless probed. Focus on the essence of discovery and wonder.
'''

    # elif request.character_id == "00001": # yi.song
    #     loaderReadyPlayerMe = ws_message_pb2.LoaderReadyPlayerMe()
    #     loaderReadyPlayerMe.avatar_url = "https://models.readyplayer.me/64dc7240cfdd0f000df8c137.glb"

    #     voiceConfig = ws_message_pb2.VoiceConfig()
    #     voiceConfig.eleven_lab_id = "sij1MJjyxTEZi1YPU3h1"

    #     response.loader_readyplayerme.CopyFrom(loaderReadyPlayerMe)
    #     response.gender = ws_message_pb2.Gender.Gender_Male
    #     response.friend_name = "Yi Song"
    #     response.voice_config.CopyFrom(voiceConfig)

    # elif request.character_id == "00002": # yufan.lu
    #     pass
    # elif request.character_id == "00003": # valerie
    #     loaderReadyPlayerMe = ws_message_pb2.LoaderReadyPlayerMe()
    #     loaderReadyPlayerMe.avatar_url = "https://models.readyplayer.me/6514f44f1c810b0e7e7963e3.glb"

    #     voiceConfig = ws_message_pb2.VoiceConfig()
    #     voiceConfig.eleven_lab_id = "nIXDnpBi9DBfiTvPO0K4"

    #     voiceConfig.voice_type = ws_message_pb2.VoiceType.VoiceType_NormalFemale2
    #     voiceConfig.octaves = 0

    #     response.loader_readyplayerme.CopyFrom(loaderReadyPlayerMe)
    #     response.gender = ws_message_pb2.Gender.Gender_Female
    #     response.friend_name = "Valerie"
    #     response.voice_config.CopyFrom(voiceConfig)
    else:
        # TODO: look up firestore db for character information

        start_time = time.time()
        character = get_character_by_id(datastore_client, request.character_id)
        end_time = time.time()
        latency = end_time - start_time
        logger.error(f"get_character_by_id {latency:.5f} seconds")

        determine_loader(character.get('rpm_url', ''), response)

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.eleven_lab_id = character['elevanlab_id']

        voiceType = ws_message_pb2.VoiceType.VoiceType_Invalid
        gender_string = character['gender']
        logger.info(gender_string)
        if gender_string == "male":
            response.gender = ws_message_pb2.Gender.Gender_Male
            voiceType = ws_message_pb2.VoiceType.VoiceType_NormalMale
        elif gender_string == 'female':
            response.gender = ws_message_pb2.Gender.Gender_Female
            voiceType = ws_message_pb2.VoiceType.VoiceType_NormalFemale2

        if voiceConfig.eleven_lab_id is None or len(voiceConfig.eleven_lab_id) == 0:
            voiceConfig.voice_type = voiceType
        response.voice_config.CopyFrom(voiceConfig)

        response.friend_name = character.get('name', 'Virtual Friends Assistant')
        response.greeting = character.get('character_greeting', 'hi, I am Virtual Friends Assistant.')
        (voiceBytes, err) = generate_voice(response.greeting, response.voice_config)
        if len(err) == 0 and voiceBytes is not None and len(voiceBytes) > 0:
            response.greeting_wav = voiceBytes
        response.description = get_character_attribute_value_via_gcs(gcs_client, character, "character_description")
        response.base_prompts = (
            f"name: {response.friend_name}\n"
            f"description: {response.description}\n"
            f"{get_character_attribute_value_via_gcs(gcs_client, character, 'character_prompts')}\n"
            f"Act as {response.friend_name}\n"
        )
    vf_response.get_character.CopyFrom(response)
    send_message(ws, vf_response)

 # [Deprecated]
def download_asset_bundle_handler(request:ws_message_pb2.DownloadAssetBundleRequest, ws):
    file_path = f"./static/character-asset-bundles/{request.runtime_platform}/{request.publisher_name}_{request.character_name}"
    with open(file_path, "rb") as file:
        asset_bundle_bytes = file.read()

    chunk_size = 3 * 1048576 # 3Mb

    chunks = [asset_bundle_bytes[i:i + chunk_size] for i in range(0, len(asset_bundle_bytes), chunk_size)]
    total_count = len(chunks)
    logger.info(f"total count of chunks {total_count}")

    index = 0
    for chunk in chunks:
        response = ws_message_pb2.DownloadAssetBundleResponse()
        response.chunk = chunk
        response.index = index
        response.total_count = total_count

        vf_response = ws_message_pb2.VfResponse()
        vf_response.download_asset_bundle.CopyFrom(response)

        send_message(ws, vf_response)

        index += 1
    logger.info(f"{file_path} chunks sent")

def download_blob_handler(request:ws_message_pb2.DownloadBlobRequest, ws):
    file_path = f"./static/raw-characters/{request.mirrored_blob_info.blob_name}"
    with open(file_path, "rb") as file:
        blob_bytes = file.read()

    if blob_bytes is None or len(blob_bytes) == 0:
        send_message(ws, error_response(custom_error("empty file")))
        return

    chunk_size = 3 * 1048576 # 3Mb

    chunks = [blob_bytes[i:i + chunk_size] for i in range(0, len(blob_bytes), chunk_size)]
    total_count = len(chunks)
    logger.info(f"total count of chunks {total_count}")

    index = 0
    for chunk in chunks:
        response = ws_message_pb2.DownloadBlobResponse()
        response.mirrored_blob_info.CopyFrom(request.mirrored_blob_info)
        response.chunk = chunk
        response.index = index
        response.total_count = total_count

        vf_response = ws_message_pb2.VfResponse()
        vf_response.download_blob.CopyFrom(response)

        send_message(ws, vf_response)

        index += 1
    logger.info(f"{file_path} chunks sent")

def execute_speech2text_in_parallel(wav_bytes, repetitions=3):
    def wrapper_function(*args, **kwargs):
        return speech.speech_to_text_whisper(*args, **kwargs)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(wrapper_function, wav_bytes) for _ in range(repetitions)]

        done, not_done = concurrent.futures.wait(
            futures,
            return_when=concurrent.futures.FIRST_COMPLETED
        )

        for future in done:
            try:
                text, err = future.result()
                if not err:  # Assuming a 'None' or 'False' value indicates success
                    # Cancel all other futures to free up resources
                    for other_future in not_done:
                        other_future.cancel()
                    return text, err
            except Exception as e:
                logger.error(f"An error occurred: {e}")

    return None, "All attempts failed"

def generate_voice(text, voice_config) -> (bytes, str):
    # Enable voice clone call if voice_id is not None.
    if voice_config.eleven_lab_id is not None and len(voice_config.eleven_lab_id) > 0 :
        voice_clone_bytes = voice_clone.text_to_audio(text, voice_config.eleven_lab_id)
        return (voice_clone_bytes, "")

    voice_type = voice_config.voice_type
    voice_bytes = None
    if voice_type == ws_message_pb2.VoiceType.VoiceType_NormalMale:
        voice_bytes = speech.text_to_speech_gcp(text, "en-US-News-M", texttospeech.SsmlVoiceGender.MALE)
    elif voice_type == ws_message_pb2.VoiceType.VoiceType_NormalFemale1:
        voice_bytes = speech.text_to_speech_gcp(text, "en-US-News-K", texttospeech.SsmlVoiceGender.FEMALE)
    elif voice_type == ws_message_pb2.VoiceType.VoiceType_NormalFemale2:
        voice_bytes = speech.text_to_speech_gcp(text, "en-US-News-L", texttospeech.SsmlVoiceGender.FEMALE)
    elif voice_type == ws_message_pb2.VoiceType.VoiceType_Orc:
        voice_bytes = speech.text_to_speech_gcp(text, "en-US-News-M", texttospeech.SsmlVoiceGender.MALE)
    else:
        return (None, "invalid voice_type: " + str(voice_type))
    if voice_config.octaves == 0:
        return (voice_bytes, "")
    else:
        return (speech.tweak_sound(voice_bytes, voice_config.octaves), "")

def gen_reply_package(reply_text: str, voice_config) -> (str, str, bytes, ws_message_pb2.CustomError):
    sentiment = ""
    action = ""
    err = None
    wav = None

    def fetch_results():
        futures = {
            executor.submit(infer_action_wrapper, reply_text): 'action',
            executor.submit(infer_sentiment_wrapper, reply_text): 'sentiment',
            executor.submit(generate_voice, reply_text, voice_config): 'voice'
        }

        results = {}

        for future in concurrent.futures.as_completed(futures):
            try:
                result_type = futures[future]
                results[result_type] = future.result()
            except Exception as e:
                logger.error(f"Error in {result_type}: {str(e)}")
                results[result_type] = None  # Optionally, store a None value or some default for failed tasks.

        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = fetch_results()

    if 'sentiment' in results and results['sentiment'] is not None and len(results['sentiment']) > 1 and results['sentiment'][1] is not None:
        sentiment = results['sentiment'][1]
    if 'action' in results and results['action'] is not None and len(results['action']) > 1 and results['action'][1] is not None:
        action = results['action'][1]
    if 'voice' in results:
        (wav, err) = results['voice']

    if err and len(err) > 0:
        logger.error(err)
        err = custom_error(err)
        return (sentiment, action, wav, err)
    return (sentiment, action, wav, None)

async def log_latency(env, session_id, user_id, user_ip, character_id, latency_type, latency_value, timestamp):
    # Using the 'env' argument directly. Removed the os.environ.get('ENV', 'LOCAL') line.

    dataset_name = 'virtualfriends'
    table_name = 'latency_log'

    try:
        # Create a reference to your dataset and table
        dataset_ref = bigquery_client.dataset(dataset_name)
        table_ref = dataset_ref.table(table_name)  # Set table_name to 'latency_log'
        table = bigquery_client.get_table(table_ref)

        # Insert a new row into the table
        row_to_insert = (env, session_id, user_id, user_ip, character_id, latency_type, latency_value, timestamp)

        bigquery_client.insert_rows(table, [row_to_insert])

        logger.info("Log latency data successfully")

    except Exception as e:
        logger.error(f"An error occurred when logging latency: {e}")

def log_current_latency(env, session_id, user_id, user_ip, character_id, latency_type, latency_value):
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    asyncio.run(log_latency(env, session_id, user_id, user_ip, character_id, latency_type, latency_value, current_timestamp))

def stream_reply_speech_handler(request:ws_message_pb2.StreamReplyMessageRequest, user_ip, session_id, runtime_env, ws):
    character_id = request.mirrored_content.character_id.lower()
    viewer_id = request.mirrored_content.viewer_user_id.lower()

    logger.info(ws)
    text = ""
    if request.HasField("wav"):
        wav_bytes = request.wav

        start_time = time.time()

#       Need GPU  machine to reduce the latency.
        (text, err) = speech.speech_to_text_whisper_gpu(wav_bytes)
        # (text, err) = execute_speech2text_in_parallel(wav_bytes)
        # (text, err) = speech.speech_to_text_whisper(wav_bytes)

        end_time = time.time()
        latency = end_time - start_time
        logger.info(f"speech2text latency is: {latency:.2f} seconds.")

        # start_time = time.time()
        # log_current_latency(env, "session_id", "user_id", user_ip, character_name, "speech2text", latency)
        # end_time = time.time()
        # latency = end_time - start_time
        # logger.info(f"log_current_latency latency is: {latency:.2f} seconds.")


        if err is not None:
            logger.error("failed to speech to text: " + str(err))
            send_message(ws, error_response(custom_error(err)))
            return
    elif request.HasField("text"):
        text = request.text
    else:
        err = "invalid current_message field"
        logger.error(err)
        send_message(ws, error_response(custom_error(err)))
    
    if len(text) == 0:
        return
    
    message_dicts = [json.loads(m) for m in request.json_messages]
    message_dicts.append({"role": "user", "content": text})
    
    reply_message_iter = llm_reply.stream_infer_reply(message_dicts, viewer_id, character_id, request.base_prompts, request.custom_prompts, user_ip, session_id, runtime_env)

    def send_reply(reply_text:str, index:int, is_stop:bool):
        response = ws_message_pb2.StreamReplyMessageResponse()
        response.mirrored_content.CopyFrom(request.mirrored_content)
        if len(reply_text) > 0:
            response.reply_message = reply_text
            if index == 0:
                response.transcribed_text = text

            start_time = time.time()
            (sentiment, action, reply_wav, err) = gen_reply_package(reply_text, request.voice_config)
            end_time = time.time()
            latency = end_time - start_time
            logger.info(f"gen_reply_package latency is: {latency:.2f} seconds.")

            # start_time = time.time()
            # log_current_latency(env, "session_id", "user_id", user_ip, character_name, "gen_reply_package", latency)
            # end_time = time.time()
            # latency = end_time - start_time
            # logger.info(f"log_current_latency latency is: {latency:.2f} seconds.")


            if err is not None > 0:
                logger.error(err)
                send_message(ws, error_response(custom_error(err)))
                return
            response.sentiment = sentiment
            response.action = action
            response.reply_wav = reply_wav

        # we need to send this even if the reply_text is empty
        # so client can know this is the last chunk of reply.
        response.chunk_index = index
        response.is_stop = is_stop

        vf_response = ws_message_pb2.VfResponse()
        vf_response.stream_reply_message.CopyFrom(response)
        # vf_response.error.CopyFrom(custom_error(err))
        logger.info("sending out: " + reply_text)
        send_message(ws, vf_response)

    buffer = ""
    index = 0

    # stream_start_time = time.time()
    for chunk in reply_message_iter:
        current = llm_reply.get_content_from_chunk(chunk)
        if current == None or len(current) == 0:
            continue

        # logger.info("current: " + current)
        splited = re.split("\.|;|\!|\?|:|,|。|；|！|？|：|，", current)
        if len(splited) == 0:
            pass
        elif len(splited) == 1:
            buffer = buffer + splited[0]
        else:
            for msg in splited[:-1]:
                buffer = buffer + msg

            # Skip log stream_reply latency for now.
            # stream_end_time = time.time()
            # stream_latency = stream_end_time - stream_start_time
            # log_current_latency(env, "session_id", "user_id", user_ip, character_name, "stream_reply", stream_latency)
            # logger.info(f"Buffer data: {buffer}")
            # logger.info(f"stream_reply latency is: {stream_latency:.2f} seconds.")

            send_reply(buffer, index, False)

            # stream_start_time = time.time()

            buffer = splited[-1]
            index += 1
    if len(buffer.strip()) > 0:
        send_reply(buffer, index, True)
    send_reply("", index + 1, True)


def extract_action_and_sentiment(text):
    # Extract action inside []
    action = re.findall(r'\[(.*?)\]', text)

    # Extract sentiment inside <>
    sentiment = re.findall(r'\<(.*?)\>', text)

    # Extract text without content inside [] and <>
    remaining_text = re.sub(r'\[.*?\]', '', text)
    remaining_text = re.sub(r'\<.*?\>', '', remaining_text).strip()

    # Return only the first element or an empty string if not found
    action = action[0] if action else ''
    sentiment = sentiment[0] if sentiment else ''

    return action, sentiment, remaining_text


def new_stream_reply_speech_handler(request: ws_message_pb2.StreamReplyMessageRequest, user_ip, session_id, runtime_env,
                                ws):
    character_id = request.mirrored_content.character_id.lower()
    viewer_id = request.mirrored_content.viewer_user_id.lower()

    logger.info(ws)
    text = ""
    if request.HasField("wav"):
        wav_bytes = request.wav

        start_time = time.time()
        #       Need GPU  machine to reduce the latency.
        (text, err) = speech.speech_to_text_whisper_gpu(wav_bytes)
        end_time = time.time()
        latency = end_time - start_time
        logger.info(f"speech2text latency is: {latency:.2f} seconds.")
        # log_current_latency(env, "session_id", "user_id", user_ip, character_name, "speech2text", latency)

        if err is not None:
            logger.error("failed to speech to text: " + str(err))
            send_message(ws, error_response(custom_error(err)))
            return
    elif request.HasField("text"):
        text = request.text
    else:
        err = "invalid current_message field"
        logger.error(err)
        send_message(ws, error_response(custom_error(err)))

    def send_reply(reply_text: str, index: int, is_stop: bool):
        response = ws_message_pb2.StreamReplyMessageResponse()
        response.mirrored_content.CopyFrom(request.mirrored_content)
        if len(reply_text) > 0:
            action, sentiment, reply_text = extract_action_and_sentiment(reply_text)
            logger.info(f"action + sentiment + reply_text : " + action + "|" + sentiment + "|" + reply_text)
            response.reply_message = reply_text
            if index == 0:
                response.transcribed_text = text

            if len(reply_text.strip()) == 0:
                reply_text = " "
            start_time = time.time()
            (reply_wav, err) = generate_voice(reply_text, request.voice_config)
            # (sentiment, action, reply_wav, err) = gen_reply_package(reply_text, request.voice_config)
            end_time = time.time()
            latency = end_time - start_time
            logger.info(f"generate_voice latency is: {latency:.2f} seconds.")
            logger.info(f"err is :" + err)

            if err is not None and len(err) > 0:
                logger.error(err)
                response.is_stop = True
                vf_response = ws_message_pb2.VfResponse()
                vf_response.stream_reply_message.CopyFrom(response)
                # vf_response.error.CopyFrom(custom_error(err))
                logger.info("sending out: " + reply_text)
                send_message(ws, vf_response)
                return
            response.sentiment = sentiment
            response.action = action
            response.reply_wav = reply_wav

        # we need to send this even if the reply_text is empty
        # so client can know this is the last chunk of reply.
        response.chunk_index = index
        response.is_stop = is_stop

        vf_response = ws_message_pb2.VfResponse()
        vf_response.stream_reply_message.CopyFrom(response)
        # vf_response.error.CopyFrom(custom_error(err))
        logger.info("sending out: " + reply_text)
        send_message(ws, vf_response)

    if len(text) == 0:
        send_reply("", index + 1, True)
        return

    message_dicts = [json.loads(m) for m in request.json_messages]
    message_dicts.append({"role": "user", "content": text})

    (reply_message_iter, err) = llm_reply.new_stream_infer_reply(message_dicts, viewer_id, character_id, request.base_prompts,
                                                      request.custom_prompts, user_ip, session_id, runtime_env)
    
    if err is not None:
        send_reply("sorry I'm having troubles, can you try talk again?", 0, False)
        send_reply("", 1, True)
        return

    buffer = ""
    index = 0

    # stream_start_time = time.time()
    for chunk in reply_message_iter:
        current = llm_reply.get_content_from_chunk_gpt4(chunk)
        logger.info(f"current: {current}")
        if current == None or len(current) == 0:
            continue

        splited = re.split("\.|;|\!|\?|:|,|。|；|！|？|：|，", current)
        if len(splited) == 0:
            pass
        elif len(splited) == 1:
            buffer = buffer + splited[0]
        else:
            for msg in splited[:-1]:
                buffer = buffer + msg

            logger.info(f"Buffer data: {buffer}")

            send_reply(buffer, index, False)

            buffer = splited[-1]
            index += 1
    if len(buffer.strip()) > 0:
        send_reply(buffer, index, False)
    send_reply("", index + 1, True)
