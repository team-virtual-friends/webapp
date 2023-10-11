import logging
import os
from flask import Flask, request
from flask_cors import CORS
from flask_sock import Sock

from web_socket.virtualfriends_proto import ws_message_pb2
from web_socket.ws_api import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Enable CORS for the Flask app
CORS(app)

sock = Sock(app)

# from torch.cuda import is_available as is_cuda_available
# device = 'cuda' if is_cuda_available() else 'cpu'
# logger.error(f"Faster Whisper Model device: {device}")


@app.route('/')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return 'Hello {}!\n'.format(target), 200

@app.route('/connect')
def on_connect(ws):
    logger.info("on_connect")
    ws.send("connect")

@app.route('/disconnect')
def on_disconnect(ws):
    logger.info("disconnected")

@sock.route('/echo')
def echo(ws):
    while True:
        data = ws.receive()
        logger.info(f"logger data: {data}")
        ws.send(data)

@sock.route("/in-game")
def in_game_handler(ws):
    while True:
        received = ws.receive()
        vf_request = ws_message_pb2.VfRequest()
        vf_request.ParseFromString(received)

        if vf_request.HasField("request"):
            if vf_request.HasField("echo"):
                echo_handler(vf_request.echo, ws)

            elif vf_request.HasField("stream_reply_message"):
                stream_reply_speech_handler(vf_request.stream_reply_message, vf_request.ip_addr, vf_request.session_id, vf_request.runtime_env, ws)

            elif vf_request.HasField("download_asset_bundle"):
                download_asset_bundle_handler(vf_request.download_asset_bundle, ws)

            elif vf_request.HasField("download_blob"):
                download_blob_handler(vf_request.download_blob, ws)

            elif vf_request.HasField("get_character"):
                get_character_handler(vf_request.get_character, ws)

            else:
                # Handle the case where the 'request' field is set but none of the specific fields are set
                ws.send(error_response("Unknown request type").SerializeToString())
        else:
            # Handle the case where the 'request' field is not set
            ws.send(error_response("No request type set").SerializeToString())

pre_download_all_asset_bundles()

if __name__ == '__main__':
    env = os.environ.get('ENV', 'LOCAL')
    if env == 'PROD':
        pass
    elif env == 'STAGING':
        from waitress import serve
        serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8107)))
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8510)))

