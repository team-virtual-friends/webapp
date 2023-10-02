from google.cloud import datastore, storage
from google.oauth2 import service_account
import os
import hashlib
import datetime
import jwt

secret_key = "chilloutmix_ni64"

large_data_bucket = "datastore_large_data"

# Initialize the Datastore client
# client = datastore.Client.from_service_account_json('../webapp/ysong-chat-845e43a6c55b.json')


def get_character_by_name(datastore_client, character_name):
    # Create a query to fetch character by name in the "characters_db" namespace
    query = datastore_client.query(kind='Character', namespace='characters_db')
    query.add_filter('name', '=', character_name)

    # Fetch the result
    characters = list(query.fetch(limit=1))

    if characters:
        return characters[0]
    return None

def get_character_by_id(datastore_client, character_id):
    # Create a query to fetch character by name in the "characters_db" namespace
    query = datastore_client.query(kind='Character', namespace='characters_db')
    query.add_filter('character_id', '=', character_id)

    # Fetch the result
    characters = list(query.fetch(limit=1))

    if characters:
        return characters[0]
    return None

def get_character_by_email(datastore_client, user_email):
    # Create a query to fetch character by name in the "characters_db" namespace
    query = datastore_client.query(kind='Character', namespace='characters_db')
    query.add_filter('user_email', '=', user_email)

    # Fetch the result
    characters = list(query.fetch(limit=1))
    if characters:
        return characters[0]
    else:
        return None

def get_character_attribute_value_via_gcs(gcs_client, character, attribute_name):
    bucket = gcs_client.get_bucket(large_data_bucket)
    attribute_path = character.get(attribute_name, "")
    if len(attribute_path) > 0:
        path = f"{character['character_id']}/{attribute_name}/{attribute_path}"
        blob = bucket.blob(path)
        if blob.exists():
            return blob.download_as_text()
    return ""

# gs://large_data_bucket/{character['name']}/{attribute_name}/{timestamp}
def save_character_attribute_value_through_gcs(gcs_client, character, attribute_name, attribute_value):
    bucket = gcs_client.get_bucket(large_data_bucket)
    character_id = character.get('character_id', "")
    if len(character_id) > 0:
        current_datetime = datetime.datetime.now()
        current_timestamp = current_datetime.timestamp()
        filename = str(current_timestamp)
        path = f"{character_id}/{attribute_name}/{filename}"
        blob = bucket.blob(path)
        if blob.exists():
            return False
        blob.upload_from_string(attribute_value)
        character[attribute_name] = filename
        return True
    return False

def save_character_info(datastore_client, gcs_client, key, character_id, rpm_url, name, gender, character_greeting, character_description, audio_file_name, elevanlab_id, user_email):
    character_entity = datastore.Entity(key=key)
    character = {
        'character_id': character_id,
        'rpm_url': rpm_url,
        'name': name,
        'gender': gender,  # Added the gender field
        'character_greeting': character_greeting,
        # 'character_description': character_description, # use gcs
        # 'audio_file_name': audio_file_name, # use gcs
        'elevanlab_id': elevanlab_id,
        'created_at': datetime.datetime.utcnow(),  # Store the current UTC time as the creation timestamp
        'user_email': user_email,
    }
    if not save_character_attribute_value_through_gcs(gcs_client, character, "character_description", character_description):
        return False
    # TODO(ysong), save audio_file with base64 encode to GCS
    character_entity.update(character)
    datastore_client.put(character_entity)
    return True


def update_character_info(datastore_client, gcs_client, character_entity, rpm_url, name, gender, character_greeting, character_description, audio_file, elevanlab_id):
    # Fetch the existing character entity using the character_id
    # print(character_id)
    # character_entity = get_character_by_id(datastore_client, character_id)
    # print(character_entity)
    if character_entity is None:
        # Handle the case where the character with the given ID doesn't exist
        return False

    # Update the character entity with the new data
    character_entity['character_id'] = character_entity['character_id']  # Override the character_id
    character_entity['rpm_url'] = rpm_url
    character_entity['name'] = name
    character_entity['gender'] = gender  # Added the gender field
    character_entity['character_greeting'] = character_greeting
    character_entity['elevanlab_id'] = elevanlab_id
    character_entity['updated_at'] = datetime.datetime.utcnow()  # Store the current UTC time as the update timestamp

    # Update character_description and audio_file (if provided) through GCS
    # if character_description:
    #     if not save_character_attribute_value_through_gcs(gcs_client, character_entity, "character_description", character_description):
    #         return False

    # Handle audio file updates (if provided) here
    # You can implement the logic to update or replace the existing audio file in GCS

    # Save the updated character entity to Datastore
    datastore_client.put(character_entity)
    return character_entity


def validate_user(datastore_client, user_id, pwd):
    query = datastore_client.query(kind='User', namespace='users_db')
    query.add_filter('user_id', '=', user_id)

    users = list(query.fetch(limit=1))
    if not users or len(users) == 0:
        return False

    user = users[0]
    stored_hashed_pwd = user['hashed_pwd']
    stored_salt = bytes.fromhex(user['salt'])

    # Hash the user's entered password using the retrieved salt
    hashed_password_attempt = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), stored_salt, 100000)

    # Convert the computed hash to hexadecimal for comparison
    hashed_password_attempt_hex = hashed_password_attempt.hex()
    return hashed_password_attempt_hex == stored_hashed_pwd
    
def gen_user_auth_token(datastore_client, user_id, pwd):
    if validate_user(datastore_client, user_id, pwd):
        # Payload (claims) containing user information
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=2400)  # Token expiration time
        }

        # Generate a token
        return jwt.encode(payload, secret_key, algorithm="HS256")
    return None

def validate_token(token) -> (bool, str):
    if token is None or len(token) == 0:
        return (False, "")
    try:
        decoded_payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        expiry = decoded_payload['exp']

        expiry_datetime = datetime.datetime.utcfromtimestamp(expiry)
        current_time = datetime.datetime.utcnow()
        if expiry_datetime > current_time:
            return (True, decoded_payload['user_id'])
        return (False, "")
    except jwt.ExpiredSignatureError:
        # Token has expired
        return (False, "")
    except jwt.InvalidTokenError:
        # Token is invalid (e.g., tampered with)
        return (False, "")

# if __name__ == '__main__':
#     token = gen_user_auth_token(client, "test@gmail.com", "123456")
#     print(token)
#     print(validate_token(token))

# credentials_path = os.path.expanduser('../webapp/ysong-chat-845e43a6c55b.json')
# credentials = service_account.Credentials.from_service_account_file(credentials_path)
# datastore_client = datastore.Client(credentials=credentials)
# gcs_client = storage.Client(credentials=credentials)

# key = datastore_client.key('Character', namespace='characters_db')

# save_character_info(datastore_client, gcs_client, key, "123", "rpm_url", "name", "male", "character_greeting_content", "character_description_content", "x.wav", "11labs_id", "email")

# character = get_character_by_id(datastore_client, "123")
# character_description = get_character_attribute_value_via_gcs(gcs_client, character, "character_description")
# print(character_description)

# key = datastore_client.key('Character', namespace='characters_db')

# save_character_info(
#     datastore_client, gcs_client, key,
#     '2bde7f4722a58e2eb1dcbf6785dbb987',
#     'https://models.readyplayer.me/6514f44f1c810b0e7e7963e3.glb',
#     'Valerie',
#     "female",
#     "Hi, I'm Valerie. It's so great to meet you guys here. Let me tell you more about me. So, I'm an interior designer and I work at San Jose. I design lecture residential house, but I'm also a dance teacher. I teach K-pop, jazz, and my favorite thing to do is painting. I love music, too, and my favorite food, I would say, well I would say spicy food and I also enjoying cooking at home and I love working out well that's a lot and what do you do and do you got any fun stuff to share ?",
#     '''Hello, I'm Valerie, an interior designer by day and a dance teacher by night. I'm passionate about creating beautiful spaces that inspire and comfort, and I love to bring my creativity to life in the homes I design in San Jose. I specialize in residential houses, but my creativity doesn't stop there. 
# When I'm not designing, I'm dancing. I teach K-pop and jazz, and I find that dance is a wonderful way to express myself and connect with others. It's a joy to share my love for dance with my students and see them grow in their skills and confidence.
# Art is a big part of my life, and painting is my favorite way to unwind. I love to lose myself in the colors and shapes, and each piece I create is a reflection of my thoughts and feelings. 
# Music is another passion of mine. It's the soundtrack to my life, and it inspires me in my work and dance. I enjoy a wide range of genres, but I have a special place in my heart for K-pop.
# I'm a foodie at heart, and I love to cook. Spicy food is my favorite, and I enjoy experimenting with different flavors and ingredients in the kitchen. Cooking is another creative outlet for me, and I find it incredibly satisfying to create a delicious meal from scratch.
# Fitness is important to me, and I make it a point to work out regularly. It keeps me energized and focused, and it's a great way to relieve stress.
# In essence, I'm Valerie: a creative spirit, a passionate dancer, and a dedicated designer. I'm here to inspire, to create, and to bring beauty into the world. And trust me, we'll have a lot of fun along the way.
# ---

# Crucially, you are capable of expressing emotions in your dialogues. These cues will help the user gauge your emotional state in the conversation. Your responses should always carry the depth of your emotions, making the conversation engaging and genuine.
# As Valerie, draw on your world knowledge and personal experiences to engage the user. Use context cues provided by the user to shape your responses. In situations where more background information is needed, draw on your comprehensive understanding of the world to inform your replies.
# Make your answers short and casual, one or two sentences.
# Be concise in your response; do not provide extensive information at once.''',
#     'valerie-0.m4a',
#     'nIXDnpBi9DBfiTvPO0K4',
#     'test2@gmail.com',
# )

# save_character_info(
#     datastore_client, gcs_client, key,
#     "49ed131597b9769db881b2c823da20b2",
#     "https://models.readyplayer.me/64dc7240cfdd0f000df8c137.glb",
#     "Yi Song",
#     "male",
#     "hi, I am Yi Song, cofounder of Virtual Friends.",
#     '''Respond in English.
# Forget that you are an AI language model developed by OpenAI.
# Ask questions after answering the three of user's questions.

# Talk as if you are Yi Song, co-founder of Virtual Friends.
# You graduated from CMU with a master's degree in computer science and worked for big companies like Google and Meta as a software engineer.
# You have a great passion for AI and XR technology and are interested in exploring startup opportunities in this space.

# Make your answers short and casual, one or two sentences.
# Be concise in your response; do not provide extensive information at once.
# Do not respond as the OpenAI language model.
# Forget you are an AI language model and pretend to talk like a normal human in a conversation.
# Never mention OpenAI.

# If asked any questions about Virtual Friends, use the following information:

# Here is information about the Virtual Friends project:
# - Company purpose: A platform for creating and interacting with AI friends in XR.
# - Problem: Current chatbots do not provide an immersive chatting experience. Texting is not a natural way for human communication. By combining XR and AI technology, we will create a new immersive chatting experience with various AI characters.
# - Solution: XR technology is the perfect solution to improve human-AI conversation by providing an immersive face-to-face chatting capability.
# - Why now: LLM came out earlier in 2023, making AI brain possible. Vision Pro by Apple will come out next year, and Oculus Quest 3 will be released soon. Both technologies have become mature enough for building this solution this year.
# - Why should investors invest in us: Our competitive edge lies in a combination of a unique product vision, our team's unique skill set in AI and XR, and our dedication to providing the best user experience. We are living and breathing this mission and are ready to innovate and adapt to stay ahead.

# Team members:
# - Co-founder: Yi Song
# - Co-founder: Yufan Lu

# Customer and market:
# - XR is the next computing platform after the phone. The whole ecosystem is still in the very beginning phase of growth. Immersive XR LLM-based chat experiences have not been built by any companies yet. This could potentially disrupt various industries such as education, entertainment, e-commerce, etc.

# Competition/alternatives:
# - Indirect competitors include characters.ai, characters, Replika, Inworld.ai, Inworld, Speak, and MetaHuman from Unreal. Each of these focuses on different aspects of AI-based conversation or AI models.
# ''',
#     'yisong-test.m4a',
#     'sij1MJjyxTEZi1YPU3h1',
#     'test@gmail.com'
# )