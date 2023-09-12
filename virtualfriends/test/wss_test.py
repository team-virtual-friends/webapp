import websocket
import time  # import the time module to add a delay

def on_message(ws, message):
    print("Received:", message)
    time.sleep(1)  # add a small delay to ensure the message is printed before closing
    ws.close()  # close the WebSocket connection after receiving a message

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("### Closed ###")

def on_open(ws):
    ws.send("Hello, yi song!")

if __name__ == "__main__":
    ws_url = "ws://virtualfriends.app/echo"
    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()