import base64
import json
import logging

from .virtualfriends_proto import ws_message_pb2

from . import speech
from . import llm_reply

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

def custom_error(exp:Exception) -> ws_message_pb2.CustomError:
    ret = ws_message_pb2.CustomError()
    ret.error_message = str(exp)
    return ret

def echo_handler(echo_request:ws_message_pb2.EchoRequest) -> (ws_message_pb2.EchoResponse, Exception):
    logger.info("echo: " + echo_request.text)
    echo_response = ws_message_pb2.EchoResponse()
    echo_response.text = echo_request.text
    return (echo_response, None)

def speech_to_text_handler(speech_to_text_request:ws_message_pb2.SpeechToTextRequest) -> (ws_message_pb2.SpeechToTextResponse, Exception):
    speech_to_text_response = ws_message_pb2.SpeechToTextResponse()
    wav_bytes = speech_to_text_request.wav
    (text, err) = speech.speech_to_text_whisper(wav_bytes)
    if err is None:
        speech_to_text_response.text = text
    return (speech_to_text_response, err)

def reply_text_handler(reply_text_message_request:ws_message_pb2.ReplyTextMessageRequest) -> (ws_message_pb2.ReplyTextMessageResponse, Exception):
    reply_text_message_response = ws_message_pb2.ReplyTextMessageResponse()

    message_dicts = [json.loads(m) for m in reply_text_message_request.json_messages]
    if len(reply_text_message_request.current_message) > 0:
        message_dicts.append({"role": "user", "content": reply_text_message_request.current_message})

    reply_message = llm_reply.infer_reply(message_dicts, reply_text_message_request.character_name)

    reply_text_message_response.reply_message = reply_message
    reply_text_message_response.action = llm_reply.infer_action(reply_message)
    reply_text_message_response.sentiment = llm_reply.infer_sentiment(reply_message)
    reply_text_message_response.reply_wav = speech.text_to_speech_gcp(reply_message)

    return (reply_text_message_response, None)

def reply_speech_handler(reply_voice_message_request:ws_message_pb2.ReplyVoiceMessageRequest) -> (ws_message_pb2.ReplyVoiceMessageResponse, Exception):
    reply_voive_message_response = ws_message_pb2.ReplyVoiceMessageResponse()

    wav_bytes = reply_voice_message_request.wav
    (text, err) = speech.speech_to_text_whisper(wav_bytes)
    if err is not None:
        return reply_voive_message_response, err

    message_dicts = [json.loads(m) for m in reply_voice_message_request.json_messages]
    message_dicts.append({"role": "user", "content": text})

    reply_message = llm_reply.infer_reply(message_dicts, reply_voice_message_request.character_name)
    reply_voive_message_response.reply_message = reply_message
    reply_voive_message_response.action = llm_reply.infer_action(reply_message)
    reply_voive_message_response.sentiment = llm_reply.infer_sentiment(reply_message)
    reply_voive_message_response.reply_wav = speech.text_to_speech_gcp(reply_message)
    reply_voive_message_response.transcribed_text = text

    return (reply_voive_message_response, None)
