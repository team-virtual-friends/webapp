import websocket
import json


def on_message(ws, message):
    print(f"Received: {message}")


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("### closed ###")


def on_open(ws):
    # Sample message to be sent to the server for the 'reply' action
    msg = {
#        "character_name": "yi_clone",
        "action": "reply",
        "message": '{"role": "user", "content": "hi, who are you?"}'
        # sample chat messages
    }

    print(f"Sending: {json.dumps(msg)}")
    ws.send(json.dumps(msg))


if __name__ == "__main__":
    websocket.enableTrace(True)

    # Assuming your server is running on localhost:8080
    # ws = websocket.WebSocketApp("ws://34.94.72.244/in-game",

    ws=websocket.WebSocketApp("ws://192.168.1.75:8080/in-game",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    ws.on_open = on_open
    ws.run_forever()
