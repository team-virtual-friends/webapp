import json
import logging
import re
import concurrent.futures
import os
import hashlib
import pathlib

from utils.read_write_lock import RWLock

from google.oauth2 import service_account
from google.cloud import texttospeech, storage

from .virtualfriends_proto import ws_message_pb2

from . import speech
from . import llm_reply

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

def send_message(ws, vf_response:ws_message_pb2.VfResponse):
    try:
        ws.send(vf_response.SerializeToString())
    except Exception as e:
        logger.error(f"Error sending WebSocket message: {str(e)}")

def pre_download_all_asset_bundles():
    gcs_path = "character-asset-bundles/WebGL"
    asset_bundle_names = [
        "idafaber_mina",
        "idafaber_jack",
        "idafaber_daniel",
        "idafaber_elena",
        "idafaber_cat",
        "idafaber_bunny",
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

    (sentiment, action, reply_wav, err) = gen_reply_package(echo_request.text, echo_request.voice_config)

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

def generate_voice(text, voice_config) -> (bytes, str):
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
    
def gen_reply_package(reply_text:str, voice_config) -> (str, str, bytes, ws_message_pb2.CustomError):
    sentiment = ""
    action = ""
    reply_wav = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        futures.append(executor.submit(infer_action_wrapper, reply_text))
        futures.append(executor.submit(infer_sentiment_wrapper, reply_text))

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result[0] == 'sentiment':
                    sentiment = result[1]
                elif result[0] == 'action':
                    action = result[1]
            except Exception as e:
                pass

    (wav, err) = generate_voice(reply_text, voice_config)
    if len(err) > 0:
        logger.error(err)
        err = custom_error(err)
        return (sentiment, action, reply_wav, err)
    reply_wav = wav
    return (sentiment, action, reply_wav, None)

def stream_reply_speech_handler(request:ws_message_pb2.StreamReplyMessageRequest, ws):
    logger.info(ws)
    text = ""
    if request.HasField("wav"):
        wav_bytes = request.wav
        # logger.info(f"start Speech2Text")
        # start_time = time.time()
        (text, err) = execute_speech2text_in_parallel(wav_bytes)
        # end_time = time.time()
        # latency = end_time - start_time
        # logger.info(f"Speech2Text request executed in {latency:.2f} seconds.")
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
    
    reply_message_iter = llm_reply.stream_infer_reply(message_dicts, request.mirrored_content.character_name.lower(), request.custom_prompts)

    def send_reply(reply_text:str, index:int, is_stop:bool):
        response = ws_message_pb2.StreamReplyMessageResponse()
        response.mirrored_content.CopyFrom(request.mirrored_content)
        if len(reply_text) > 0:
            response.reply_message = reply_text
            if index == 0:
                response.transcribed_text = text

            (sentiment, action, reply_wav, err) = gen_reply_package(reply_text, request.voice_config)
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
            send_reply(buffer, index, False)
            buffer = splited[-1]
            index += 1
    if len(buffer.strip()) > 0:
        send_reply(buffer, index, True)
    send_reply("", index + 1, True)
