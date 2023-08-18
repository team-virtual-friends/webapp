import socketio

sio = socketio.Client()

conversation_history = [{"role": "system", "content": " You are a hot young friendly girl. Your answer is short than 100 token normally."}]

@sio.on('connect')
def on_connect():
    print('Connected to server')

@sio.on('connected')
def on_connected(data):
    print('Server response:', data['message'])
    send_user_message()  # Send the first user message after connecting

@sio.on('chat_response')
def on_chat_response(data):
    print('Assistant Response:', data['assistant_response'])
    print('Action:', data['action'])
    print('sentiment:', data['sentiment'])
    print('messages:', data['messages'])

    # You can update your UI or perform actions with the assistant's response here
    conversation_history.append({'role': 'system', 'content': data['assistant_response']})
    send_user_message()  # Send another user message after receiving the assistant's response

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected from server')
    # You can handle UI changes or cleanup on disconnection here

def send_user_message():
    user_input = input('Enter your message: ')
    conversation_history.append({'role': 'user', 'content': user_input})
    sio.emit('chat_message', {'user_input': user_input, 'messages': conversation_history})


if __name__ == '__main__':
    sio.connect("https://ysong-chat.uc.r.appspot.com")  # Adjust the URL to your server

#    sio.connect('http://localhost:5011')  # Adjust the URL to your server
    sio.wait()