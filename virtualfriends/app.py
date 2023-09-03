import logging
import os

from flask import Flask, request, jsonify
from flask_sock import Sock

from web_socket.virtualfriends_proto import ws_message_pb2

from web_socket.ws_api import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sock = Sock(app)

@app.route('/')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return 'Hello {}!\n'.format(target)

@sock.route('/echo')
def echo(ws):
    while True:
        data = ws.receive()
        logger.info(f"logger data: {data}")
        sock.send(data)

@sock.route("/in-game")
def in_game_handler(ws):
    while True:
        received = ws.receive()
        vf_request = ws_message_pb2.VfRequest()
        vf_request.ParseFromString(received)

        vf_response = ws_message_pb2.VfResponse()
        vf_response.identifier = vf_request.identifier

        if vf_request.identifier == 'echo':
            echo_request = ws_message_pb2.EchoRequest()
            echo_request.ParseFromString(vf_request.raw)
            (echo_response, err) = echo_handler(echo_request)
            vf_response.raw = echo_response.SerializeToString()
            vf_response.error.CopyFrom(custom_error(err))

        elif vf_request.identifier == 'speech2text':
            speech_to_text_request = ws_message_pb2.SpeechToTextRequest()
            speech_to_text_request.ParseFromString(vf_request.raw)
            (speech_to_text_response, err) = speech_to_text_handler(speech_to_text_request)
            vf_response.raw = speech_to_text_response.SerializeToString()
            vf_response.error.CopyFrom(custom_error(err))

        elif vf_request.identifier == 'reply_text':
            reply_text_message_request = ws_message_pb2.ReplyTextMessageRequest()
            reply_text_message_request.ParseFromString(vf_request.raw)
            (reply_text_message_response, err) = reply_text_handler(reply_text_message_request)
            vf_response.raw = reply_text_message_response.SerializeToString()
            vf_response.error.CopyFrom(custom_error(err))

        elif vf_request.identifier == 'reply_speech':
            reply_voice_message_request = ws_message_pb2.ReplyVoiceMessageRequest()
            reply_voice_message_request.ParseFromString(vf_request.raw)
            (reply_voice_message_response, err) = reply_speech_handler(reply_voice_message_request)
            vf_response.raw = reply_voice_message_response.SerializeToString()
            vf_response.error.CopyFrom(custom_error(err))

        else:
            vf_response.error = custom_error("unknown identifier")

        ws.send(vf_response.SerializeToString())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8086)))
