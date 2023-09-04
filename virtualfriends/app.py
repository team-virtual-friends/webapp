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

        if vf_request.HasField("request"):
            if vf_request.HasField("echo"):
                (echo_response, err) = echo_handler(vf_request.echo)
                vf_response.echo.CopyFrom(echo_response)
                vf_response.error.CopyFrom(custom_error(err))
    
            elif vf_request.HasField("speech_to_text"):
                (speech_to_text_response, err) = speech_to_text_handler(vf_request.speech_to_text)
                vf_response.speech_to_text.CopyFrom(speech_to_text_response)
                vf_response.error.CopyFrom(custom_error(err))
    
            elif vf_request.HasField("reply_text_message"):
                (reply_text_message_response, err) = reply_text_handler(vf_request.reply_text_message)
                vf_response.reply_text_message.CopyFrom(reply_text_message_response)
                vf_response.error.CopyFrom(custom_error(err))
    
            elif vf_request.HasField("reply_voice_message"):
                (reply_voice_message_response, err) = reply_speech_handler(vf_request.reply_voice_message)
                vf_response.reply_voice_message.CopyFrom(reply_voice_message_response)
                vf_response.error.CopyFrom(custom_error(err))
    
            else:
                # Handle the case where the 'request' field is set, but none of the specific fields are set
                vf_response.error.CopyFrom(custom_error("Unknown request type"))
        else:
            # Handle the case where the 'request' field is not set
            vf_response.error.CopyFrom(custom_error("No request type set"))

        ws.send(vf_response.SerializeToString())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8086)))
