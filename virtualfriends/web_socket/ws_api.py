import base64
import json
import logging
import re

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

def echo_handler(echo_request:ws_message_pb2.EchoRequest, ws):
    logger.info("echo: " + echo_request.text)

    echo_response = ws_message_pb2.EchoResponse()
    echo_response.text = echo_request.text

    vf_response = ws_message_pb2.VfResponse()
    vf_response.echo.CopyFrom(echo_response)
    # vf_response.error.CopyFrom(custom_error(err))
    
    ws.send(vf_response.SerializeToString())

def speech_to_text_handler(speech_to_text_request:ws_message_pb2.SpeechToTextRequest, ws):
    speech_to_text_response = ws_message_pb2.SpeechToTextResponse()
    wav_bytes = speech_to_text_request.wav
    (text, err) = speech.speech_to_text_whisper(wav_bytes)
    if err is None:
        speech_to_text_response.text = text
    
    vf_response = ws_message_pb2.VfResponse()
    vf_response.speech_to_text.CopyFrom(speech_to_text_response)
    vf_response.error.CopyFrom(custom_error(err))
    
    ws.send(vf_response.SerializeToString())

def reply_text_handler(reply_text_message_request:ws_message_pb2.ReplyTextMessageRequest, ws):
    reply_text_message_response = ws_message_pb2.ReplyTextMessageResponse()

    message_dicts = [json.loads(m) for m in reply_text_message_request.json_messages]
    if len(reply_text_message_request.current_message) > 0:
        message_dicts.append({"role": "user", "content": reply_text_message_request.current_message})

    reply_message = llm_reply.infer_reply(message_dicts, reply_text_message_request.character_name)

    reply_text_message_response.reply_message = reply_message
    reply_text_message_response.action = llm_reply.infer_action(reply_message)
    reply_text_message_response.sentiment = llm_reply.infer_sentiment(reply_message)
    reply_text_message_response.reply_wav = speech.text_to_speech_gcp(reply_message)

    vf_response = ws_message_pb2.VfResponse()
    vf_response.reply_text_message.CopyFrom(reply_text_message_response)
    # vf_response.error.CopyFrom(custom_error(err))
    
    ws.send(vf_response.SerializeToString())

def reply_speech_handler(reply_voice_message_request:ws_message_pb2.ReplyVoiceMessageRequest, ws):
    reply_voive_message_response = ws_message_pb2.ReplyVoiceMessageResponse()

    wav_bytes = reply_voice_message_request.wav
    (text, err) = speech.speech_to_text_whisper(wav_bytes)
    if err is not None:
        logger.error("failed to speech to text: " + str(err))
        ws.send(error_response(custom_error(err)))
        return

    message_dicts = [json.loads(m) for m in reply_voice_message_request.json_messages]
    message_dicts.append({"role": "user", "content": text})

    reply_message = llm_reply.infer_reply(message_dicts, reply_voice_message_request.character_name)
    reply_voive_message_response.reply_message = reply_message
    # reply_voive_message_response.action = llm_reply.infer_action(reply_message)
    # reply_voive_message_response.sentiment = llm_reply.infer_sentiment(reply_message)
    reply_voive_message_response.reply_wav = speech.text_to_speech_gcp(reply_message)
    reply_voive_message_response.transcribed_text = text

    vf_response = ws_message_pb2.VfResponse()
    vf_response.reply_voice_message.CopyFrom(reply_voive_message_response)
    # vf_response.error.CopyFrom(custom_error(err))

    ws.send(vf_response.SerializeToString())

def stream_reply_speech_handler(stream_reply_voice_message_request:ws_message_pb2.StreamReplyVoiceMessageRequest, ws):
    wav_bytes = stream_reply_voice_message_request.wav
    (text, err) = speech.speech_to_text_whisper(wav_bytes)
    if err is not None:
        logger.error("failed to speech to text: " + str(err))
        ws.send(error_response(custom_error(err)))
        return
    
    message_dicts = [json.loads(m) for m in stream_reply_voice_message_request.json_messages]
    message_dicts.append({"role": "user", "content": text})
    
    reply_message_iter = llm_reply.stream_infer_reply(message_dicts, stream_reply_voice_message_request.character_name, 10)

    def send_reply(reply_text:str, index:int, is_stop:bool):
        stream_reply_voice_message_response = ws_message_pb2.StreamReplyVoiceMessageResponse()
        stream_reply_voice_message_response.reply_message = reply_text
        # stream_reply_voice_message_response.action = llm_reply.infer_action(reply_text)
        # stream_reply_voice_message_response.sentiment = llm_reply.infer_sentiment(reply_text)
        if index == 0:
            stream_reply_voice_message_response.transcribed_text = text
        stream_reply_voice_message_response.reply_wav = speech.text_to_speech_gcp(reply_text)
        stream_reply_voice_message_response.chunk_index = index
        stream_reply_voice_message_response.session_id = stream_reply_voice_message_request.session_id
        stream_reply_voice_message_response.is_stop = is_stop

        vf_response = ws_message_pb2.VfResponse()
        vf_response.stream_reply_voice_message.CopyFrom(stream_reply_voice_message_response)
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

        logger.info("current: " + current)
        splited = re.split("\.|;|\!|\?", current)
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
