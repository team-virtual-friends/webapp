import json
import logging
import re
import concurrent.futures
import time

from google.cloud import texttospeech

from .virtualfriends_proto import ws_message_pb2

from . import speech
from . import llm_reply

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

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
    echo_response.text = echo_request.text

    vf_response = ws_message_pb2.VfResponse()
    vf_response.echo.CopyFrom(echo_response)
    # vf_response.error.CopyFrom(custom_error(err))
    
    ws.send(vf_response.SerializeToString())

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
    
    reply_message_iter = llm_reply.stream_infer_reply(message_dicts, request.mirrored_content.character_name, 10)

    def send_reply(reply_text:str, index:int, is_stop:bool):
        response = ws_message_pb2.StreamReplyMessageResponse()
        response.mirrored_content.CopyFrom(request.mirrored_content)
        if len(reply_text) > 0:
            response.reply_message = reply_text

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                futures.append(executor.submit(infer_action_wrapper, reply_text))
                futures.append(executor.submit(infer_sentiment_wrapper, reply_text))

                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result[0] == 'sentiment':
                            response.sentiment = result[1]
                        elif result[0] == 'action':
                            response.action = result[1]
                    except Exception as e:
                        pass

            if index == 0:
                response.transcribed_text = text
            (wav, err) = generate_voice(reply_text, request.voice_config)
            if len(err) > 0:
                logger.error(err)
                ws.send(error_response(custom_error(err)))
                return
            response.reply_wav = wav
        # we need to send this even if the reply_text is empty
        # so client can know this is the last chunk of reply.
        response.chunk_index = index
        response.is_stop = is_stop

        vf_response = ws_message_pb2.VfResponse()
        vf_response.stream_reply_message.CopyFrom(response)
        # vf_response.error.CopyFrom(custom_error(err))

        ws.send(vf_response.SerializeToString())

    buffer = ""
    index = 0
    for chunk in reply_message_iter:
        current = llm_reply.get_content_from_chunk(chunk)
        if current == None:
            if len(buffer.strip()) > 0:
                send_reply(buffer, index, False)
            continue

        # logger.info("current: " + current)
        splited = re.split("\.|;|\!|\?|:|,", current)
        if len(splited) == 0:
            pass
        elif len(splited) == 1:
            buffer = buffer + splited[0]
        else:
            for msg in splited[:-1]:
                buffer = buffer + msg
            logger.info("buffer: " + buffer)
            send_reply(buffer, index, False)
            buffer = splited[-1]
            index += 1
    send_reply("", index, True)
