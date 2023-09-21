import json
import logging
import re
import concurrent.futures
import os
import tempfile

from utils.read_write_lock import RWLock

import diskcache

from google.oauth2 import service_account
from google.cloud import texttospeech, storage

from .virtualfriends_proto import ws_message_pb2

from . import speech
from . import llm_reply

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
gcsClient = storage.Client(credentials=credentials)

cachePath = f"{tempfile.gettempdir()}/gcs_asset_bundles"
gcsCache = diskcache.Cache(cachePath, expire=10800) # 3 hours
gcsLock = RWLock()

def custom_error(exp:Exception) -> ws_message_pb2.CustomError:
    ret = ws_message_pb2.CustomError()
    ret.error_message = str(exp)
    return ret

def error_response(err:ws_message_pb2.CustomError) -> ws_message_pb2.VfResponse:
    vf_response = ws_message_pb2.VfResponse()
    vf_response.error.CopyFrom(err)
    return vf_response.SerializeToString()

def infer_sentiment_wrapper(text:str) -> (str, str):
    return ("sentiment", llm_reply.infer_sentiment(text))

def infer_action_wrapper(text:str) -> (str, str):
    return ("action", llm_reply.infer_action(text))

def echo_handler(echo_request:ws_message_pb2.EchoRequest, ws):
    logger.info("echo: " + echo_request.text)

    echo_response = ws_message_pb2.EchoResponse()

    (sentiment, action, reply_wav, err) = gen_reply_package(echo_request.text, echo_request.voice_config)

    if err is not None:
        ws.send(error_response(err))
        return

    echo_response.text = echo_request.text
    echo_response.sentiment = sentiment
    echo_response.action = action
    echo_response.reply_wav = reply_wav

    vf_response = ws_message_pb2.VfResponse()
    vf_response.echo.CopyFrom(echo_response)
    # vf_response.error.CopyFrom(custom_error(err))
    
    ws.send(vf_response.SerializeToString())

def download_asset_bundle_handler(request:ws_message_pb2.DownloadAssetBundleRequest, ws):
    chunk_size = 3 * 1048576 # 3Mb

    bucket = gcsClient.get_bucket("vf-unity-data")
    folder = "character-asset-bundles"
    asset_bundle_name = f"{request.publisher_name}_{request.character_name}"
    asset_bundle_path = f"{folder}/{request.runtime_platform}/{asset_bundle_name}"

    gcsLock.r_acquire()
    asset_bundle_bytes = gcsCache.get(asset_bundle_path)
    gcsLock.r_release()

    if asset_bundle_bytes is None:
        logger.info("downloading asset_bundle...")
        asset_bundle_blob = bucket.blob(asset_bundle_path)

        if not asset_bundle_blob.exists():
            logger.error(f"{asset_bundle_path} does not exist")
            ws.send(error_response(custom_error(Exception("blob does not exist"))))
            return
        
        asset_bundle_bytes = asset_bundle_blob.download_as_bytes()

        gcsLock.w_acquire()
        # check again to see if the content has been written by another thread.
        if gcsCache.get(asset_bundle_path) is None:
            gcsCache.set(asset_bundle_path, asset_bundle_bytes)
        gcsLock.w_release()
    else:
        logger.info("found asset_bundle in cache, continue...")

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

        ws.send(vf_response.SerializeToString())

        index += 1
    logger.info(f"{asset_bundle_path} chunks sent")

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
            ws.send(error_response(custom_error(err)))
            return
    elif request.HasField("text"):
        text = request.text
    else:
        err = "invalid current_message field"
        logger.error(err)
        ws.send(error_response(custom_error(err)))
    
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
                ws.send(error_response(custom_error(err)))
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
        ws.send(vf_response.SerializeToString())

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
