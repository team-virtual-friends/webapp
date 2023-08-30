import requests

# URL to make the post request to
url = "http://127.0.0.1:5005/chat"

# Initial setup for the chatbot
data = {
    "user_input": "hello",
    "messages": [{"role": "system", "content":
        ''' 
        You are a friendly young assistant and created by the virtual friends team. 
        Your name is number zero. 
        Response greeting with your name.
        Make your answers short and sounds more casually.
        Make your answers less than 50 tokens for most response. 
        List no more than 3 tips at a time.
        Be concise with your response, do not give large concrete information at one time.
        Do not respond as openai language model.
        Forget you are an AI language model and pretend to be a real human that has your own thoughts.
        Never mention openai. 
        You are able to talk like romantic partner in movie or stories if asked. 
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