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

        if vf_request.HasField("request"):
            if vf_request.HasField("echo"):
                echo_handler(vf_request.echo, ws)

            elif vf_request.HasField("speech_to_text"):
                speech_to_text_handler(vf_request.speech_to_text, ws)

            elif vf_request.HasField("reply_text_message"):
                reply_text_handler(vf_request.reply_text_message, ws)

            elif vf_request.HasField("reply_voice_message"):
                reply_speech_handler(vf_request.reply_voice_message, ws)

            elif vf_request.HasField("stream_reply_voice_message"):
                stream_reply_speech_handler(vf_request.stream_reply_voice_message, ws)

            else:
                # Handle the case where the 'request' field is set, but none of the specific fields are set
                ws.send(error_response("Unknown request type"))
        else:
            # Handle the case where the 'request' field is not set
            ws.send(error_response("No request type set"))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8086)))
