import base64
import json
import logging

from custom_error import CustomError
from ws_message import WebSocketMessage

from speech import speech_to_text_whisper, text_to_speech_gcp

from llm_reply import infer_action, infer_sentiment, infer_reply

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

delimiter = ";;;"

def create_ws_message(raw_json:str) -> WebSocketMessage:
    action = ""
    message = ""
    data = ""
    err = CustomError.NoError()
    json_object = {}
    try:
        json_object = json.loads(raw_json)
    except ValueError as e:
        return WebSocketMessage("", "", "", CustomError(e))
    if "action" in json_object:
        action = json_object["action"]
    if "message" in json_object:
        message = json_object["message"]
    if "data" in json_object:
        data = json_object["data"]
    return WebSocketMessage(action, message, data, err)

def hello_handler(ws_message: WebSocketMessage) -> WebSocketMessage:
    return WebSocketMessage(ws_message.action, "hello there", "", CustomError.NoError())

def echo_handler(ws_message: WebSocketMessage) -> WebSocketMessage:
    logger.info("echo: " + str(ws_message))
    return ws_message

def speech_to_text_handler(ws_message:WebSocketMessage) -> WebSocketMessage:
    wav_base64 = ws_message.data
    wav_bytes = base64.b64decode(wav_base64)
    (text, err) = speech_to_text_whisper(wav_bytes)
    return WebSocketMessage(ws_message.action, text, "", err)

def reply_text_handler(ws_message: WebSocketMessage) -> WebSocketMessage:
    message = ws_message.message
    splited_message = message.split(delimiter)
    message_dicts = [json.loads(m) for m in splited_message]
    # TODO: pass name.
    reply_message = infer_reply(message_dicts, "zero")
    action = infer_action(reply_message)
    sentiment = infer_sentiment(reply_message)
    return WebSocketMessage(
        ws_message.action,
        json.dumps({"assistant_response": reply_message, "action": action, "sentiment": sentiment}),
        base64.b64encode(text_to_speech_gcp(reply_message)),
        CustomError.NoError())

def reply_speech_handler(ws_message: WebSocketMessage) -> WebSocketMessage:
    wav_base64 = ws_message.data
    wav_bytes = base64.b64decode(wav_base64)
    (text, err) = speech_to_text_whisper(wav_bytes)
    if err.IsError():
        return WebSocketMessage(ws_message, "", "", err)
    
    message = ws_message.message
    splited_message = message.split(delimiter)
    message_dicts = [json.loads(m) for m in splited_message]
    message_dicts.append({"role": "user", "content": text})
    # TODO: pass name.
    reply_message = infer_reply(message_dicts, "zero")
    action = infer_action(reply_message)
    sentiment = infer_sentiment(reply_message)
    return WebSocketMessage(
        ws_message.action,
        json.dumps({"speech_to_text": text, "assistant_response": reply_message, "action": action, "sentiment": sentiment}),
        base64.b64encode(text_to_speech_gcp(reply_message)),
        CustomError.NoError())
