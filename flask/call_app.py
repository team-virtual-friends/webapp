import requests

# URL to make the post request to
url = "http://127.0.0.1:5004/chat"

# Initial setup for the chatbot
data = {
    "user_input": "hello",
    "messages": [{"role": "system", "content":
        ''' 
        You are a beautiful young friendly assistant and are created by the virtual friends team. 
        Your name is number zero. 
        Response greeting with your name.
        Your answer should be short than 100 token normally. 
        Do not respond as openai language model.
        
        '''}]
}


def send_message(message):
    # Append user message to conversation history
    data['user_input'] = message

    # Make the post request
    response = requests.post(url, json=data)
    ai_response = response.json()

    # Append AI response to conversation history
    data['messages'] = ai_response['messages']

    print(data)

    # Print the conversation
    # for message in data['messages']:
    #     role = message.get('role', 'Unknown')
    #     content = message.get('content', 'Content missing')
    #     print(f"{role}: {content}")

    return ai_response


if __name__ == "__main__":
    while True:
        user_message = input("You: ")
        if user_message.lower() in ["quit", "exit"]:
            break
        ai_response = send_message(user_message)
        print(
            f"AI: {ai_response['assistant_response']}")  # Assuming the response structure contains a 'content' key for the AI's message