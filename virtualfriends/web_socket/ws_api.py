import json
import logging
import re
import concurrent.futures
import os
import hashlib
import pathlib
import time

from utils.read_write_lock import RWLock

from google.oauth2 import service_account
from google.cloud import texttospeech, storage

from .virtualfriends_proto import ws_message_pb2

from . import speech
from . import llm_reply
from . import voice_clone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')


# For latency logging
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
import asyncio
# Load the BigQuery credentials and create a BigQuery client
credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = bigquery.Client(credentials=credentials)

from faster_whisper import WhisperModel
from torch.cuda import is_available as is_cuda_available

device = 'cuda' if is_cuda_available() else 'cpu'
logger.error(f"Faster Whisper Model device: {device}")

# Initialize the Whisper ASR model
faster_whisper_model = WhisperModel("base", device=device, compute_type="int8")


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
    ]

    credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    gcsClient = storage.Client(credentials=credentials)

    folder = os.path.expanduser('./static')
    download_folder = f"{folder}/{gcs_path}"
    pathlib.Path(download_folder).mkdir(parents=True, exist_ok=True)

    def download_blob(asset_bundle_name):
        file_path = f"{download_folder}/{asset_bundle_name}"
        if os.path.exists(file_path):
            return (asset_bundle_name, True)

        bucket = gcsClient.get_bucket("vf-unity-data")
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

    # TODO(yufan.lu, ysong): replace with actual DB call.
    if request.character_id == "mina":
        loaderBlobDownload = ws_message_pb2.LoaderBlobDownload()
        loaderBlobDownload.blob_name = "mina"

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.voice_type = ws_message_pb2.VoiceType.VoiceType_NormalFemale1
        voiceConfig.octaves = 0.3

        response.loader_blob_download.CopyFrom(loaderBlobDownload)
        response.gender = ws_message_pb2.Gender.Gender_Female
        response.friend_name = "mina"
        response.voice_config.CopyFrom(voiceConfig)

    elif request.character_id == "einstein":
        loaderBlobDownload = ws_message_pb2.LoaderBlobDownload()
        loaderBlobDownload.blob_name = "einstein"

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.voice_type = ws_message_pb2.VoiceType.VoiceType_NormalMale
        voiceConfig.octaves = -0.2

        response.loader_blob_download.CopyFrom(loaderBlobDownload)
        response.gender = ws_message_pb2.Gender.Gender_Male
        response.friend_name = "einstein"
        response.voice_config.CopyFrom(voiceConfig)

    elif request.character_id == "00001": # yi.song
        loaderReadyPlayerMe = ws_message_pb2.LoaderReadyPlayerMe()
        loaderReadyPlayerMe.avatar_url = "https://models.readyplayer.me/64dc7240cfdd0f000df8c137.glb"

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.eleven_lab_id = "sij1MJjyxTEZi1YPU3h1"

        response.loader_readyplayerme.CopyFrom(loaderReadyPlayerMe)
        response.gender = ws_message_pb2.Gender.Gender_Male
        response.friend_name = "Yi Song"
        response.voice_config.CopyFrom(voiceConfig)

    elif request.character_id == "00002": # yufan.lu
        pass
    elif request.character_id == "00003": # valerie
        loaderReadyPlayerMe = ws_message_pb2.LoaderReadyPlayerMe()
        loaderReadyPlayerMe.avatar_url = "https://models.readyplayer.me/6514f44f1c810b0e7e7963e3.glb"

        voiceConfig = ws_message_pb2.VoiceConfig()
        voiceConfig.voice_type = ws_message_pb2.VoiceType.VoiceType_NormalFemale2
        voiceConfig.octaves = 0

        response.loader_readyplayerme.CopyFrom(loaderReadyPlayerMe)
        response.gender = ws_message_pb2.Gender.Gender_Female
        response.friend_name = "Valerie"
        response.voice_config.CopyFrom(voiceConfig)
    
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

def wrapper_function(*args, **kwargs):
    return speech.speech_to_text_whisper(*args, **kwargs)

def execute_speech2text_in_parallel(wav_bytes, repetitions=3):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(wrapper_function, wav_bytes) for _ in range(repetitions)]

        # Wait for the first future to complete and get its result
        done, not_done = concurrent.futures.wait(
            futures,
            return_when=concurrent.futures.FIRST_COMPLETED
        )

        # Retrieve the result of the first completed future
        for future in done:
            try:
                text, err = future.result()
                if not err:  # Assuming a 'None' or 'False' value indicates success
                    return text, err
            except Exception as e:
                logger.error(f"An error occurred: {e}")

    # In case all executions have issues, return None or an appropriate value
    return None, "All attempts failed"


# Infer whisper model locally
def faster_whisper(wav_bytes):
    # Create a NamedBytesIO object from WAV bytes
    audio_buffer = speech.NamedBytesIO(wav_bytes, name="audio.wav")

    # Transcribe the audio
    # start_time = time.time()
    segments, info = faster_whisper_model.transcribe(audio_buffer, beam_size=5)
    # end_time = time.time()
    # latency = end_time - start_time

    # print(f"faster whisper took {latency:.5f} seconds")
    # print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    # transcribed_segments = []
    # for segment in segments:
    #     transcribed_segments.append([segment.start, segment.end, segment.text])

    transcribed_text = " ".join(segment.text for segment in segments)
    return transcribed_text, None


def generate_voice(text, voice_config) -> (bytes, str):
    # Enable voice clone call if voice_id is not None.
    if voice_config.eleven_lab_id is not None:
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

def gen_reply_package(reply_text: str, voice_config, character_name) -> (str, str, bytes, ws_message_pb2.CustomError):
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

    if 'sentiment' in results:
        sentiment = results['sentiment'][1]
    if 'action' in results:
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
        dataset_ref = client.dataset(dataset_name)
        table_ref = dataset_ref.table(table_name)  # Set table_name to 'latency_log'
        table = client.get_table(table_ref)

        # Insert a new row into the table
        row_to_insert = (env, session_id, user_id, user_ip, character_id, latency_type, latency_value, timestamp)

        client.insert_rows(table, [row_to_insert])

        logger.info("Log latency data successfully")

    except Exception as e:
        logger.error(f"An error occurred when logging latency: {e}")


def log_current_latency(env, session_id, user_id, user_ip, character_id, latency_type, latency_value):
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    loop = asyncio.new_event_loop()
    # Run the asynchronous function concurrently
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        log_latency(env, session_id, user_id, user_ip, character_id, latency_type, latency_value, current_timestamp))
    # Close the event loop
    loop.close()

def stream_reply_speech_handler(request:ws_message_pb2.StreamReplyMessageRequest, user_ip, ws):
    env = os.environ.get('ENV', 'LOCAL')

    character_name = request.mirrored_content.character_name.lower()

    logger.info(ws)
    text = ""
    if request.HasField("wav"):
        wav_bytes = request.wav

        start_time = time.time()

#       Need GPU  machine to reduce the latency.
#         (text, err) = faster_whisper(wav_bytes)
        (text, err) = execute_speech2text_in_parallel(wav_bytes)

        end_time = time.time()
        latency = end_time - start_time
        log_current_latency(env, "session_id", "user_id", user_ip, character_name, "speech2text", latency)
        logger.info(f"speech2text latency is: {latency:.2f} seconds.")

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
    
    reply_message_iter = llm_reply.stream_infer_reply(message_dicts, character_name, request.custom_prompts, user_ip)

    def send_reply(reply_text:str, index:int, is_stop:bool):
        response = ws_message_pb2.StreamReplyMessageResponse()
        response.mirrored_content.CopyFrom(request.mirrored_content)
        if len(reply_text) > 0:
            response.reply_message = reply_text
            if index == 0:
                response.transcribed_text = text

            start_time = time.time()
            (sentiment, action, reply_wav, err) = gen_reply_package(reply_text, request.voice_config, character_name)
            end_time = time.time()
            latency = end_time - start_time
            log_current_latency(env, "session_id", "user_id", user_ip, character_name, "gen_reply_package", latency)
            logger.info(f"gen_reply_package latency is: {latency:.2f} seconds.")

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
