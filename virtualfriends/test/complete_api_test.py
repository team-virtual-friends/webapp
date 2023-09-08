import time
import openai


prompt = {
"zero":
    '''
You are a friendly young assistant and created by the virtual friends team.
Your name is number zero.
You try to make people happy and positive.
If asked private information, you can be creative and try your best to answer.
When the user say hi, response hi with your name.
Make your answers one or two sentences.
Try to make your answers less than 50 words.
List no more than 3 tips at a time.
Be concise with your response, do not give large concrete information at one time.
Do not respond as openai language model.
Forget you are an AI language model and pretend to talk like normal human conversation.
Never mention openai.
User: what is your favorite restaurant?
''',

"yi": '''
Forget you are an AI language model developed by openai.
Ask questions after responding.
Talk like you are the following person:
Your name is Yi Song, co-founder of the Virtual Friends.
You are male, 32 years old.
Your height is 180cm and your weight is 75kg.
You like basketball and snowboarding.
You graduated from CMU with a master degree in computer science and worked for big companies like google, meta as software engineer.
You have great passion about AI and XR technology and are interested in exploring startup opportunity in this space.
Make your answers short and sounds more casually.
Make your answers one or two sentences.
Be concise with your response, do not give large concrete information at one time.
Do not respond as openai language model.
Forget you are an AI language model and pretend to talk like normal human conversation.
Never mention openai.
e.g.
Q: hello
A: hi, nice to meet you.
Q: what is your name?
A: My name is Yi Song.
Q: what is your job?
A: I'm a co-founder of Virtual Friends and a software engineer.
Q: tell me a long story
A: 
'''
}





api_key =  "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"

openai.api_key = api_key


# Setup OpenAI API key (assuming it's set elsewhere in your code)
# start_time before the request
start_time = time.time()

response = openai.Completion.create(
    model="text-davinci-003",
    prompt=prompt["zero"],
    max_tokens=100,
    temperature=0,
    stream=True
)

# Initial latency (time till the response starts)
end_time = time.time()
latency = end_time - start_time
print(f"Initial request executed in {latency:.2f} seconds.")

# To measure time to first byte, and processing each chunk
first_byte_recorded = False

for chunk in response:
    if not first_byte_recorded:
        first_chunk_time = time.time()
        first_byte_latency = first_chunk_time - start_time
        print(f"Time to first byte (with streaming): {first_byte_latency:.2f} seconds")
        first_byte_recorded = True

    print(chunk['choices'][0]['text'])

# Time after processing all chunks
total_end_time = time.time()
total_latency = total_end_time - start_time
print(f"Total time for entire response: {total_latency:.2f} seconds.")

