import requests

url = "https://ysong-chat.uc.r.appspot.com/chat"

data = {
    "user_input": "u r so hot!",
    "messages": [{"role": "system", "content": " You are a hot young friendly girl. Your answer is short than 100 token normally."}]
}

print(url)

response = requests.post(url, json=data)

print(response.text)  # Add this line to print the server response before decoding it
print(response.json())