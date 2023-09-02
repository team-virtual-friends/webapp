import logging
import os

from flask import Flask, request, jsonify
from flask_sock import Sock

from web_socket.custom_error import CustomError
from web_socket.ws_message import WebSocketMessage
from web_socket.ws_api import create_ws_message, hello_handler, echo_handler, speech_to_text_handler, reply_text_handler, reply_speech_handler

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
def echo(sock):
    while True:
        data = sock.receive()
        logger.info(f"logger data: {data}")
        sock.send(data)

@sock.route("/in-game")
def in_game_handler(ws):
    while True:
        received = ws.received()
        ws_message = create_ws_message(received)

        ret_ws_message = WebSocketMessage(ws_message.action, "", "", CustomError("unknown action"))
        if ws_message.action == 'hello':
            ret_ws_message = hello_handler(ws_message)
        elif ws_message.action == 'echo':
            ret_ws_message = echo_handler(ws_message)
        elif ws_message.action == 'speech2text':
            ret_ws_message = speech_to_text_handler(ws_message)
        elif ws_message.action == 'reply_text':
            ret_ws_message = reply_text_handler(ws_message)
        elif ws_message.action == 'reply_speech':
            ret_ws_message = reply_speech_handler(ws_message)

        ws.send(ret_ws_message.to_json())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8086)))
