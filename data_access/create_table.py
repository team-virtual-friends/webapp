from google.cloud import datastore
import os
import hashlib

# Initialize client
client = datastore.Client.from_service_account_json('../webapp/ysong-chat-845e43a6c55b.json')


def create_and_insert_user(user_id, pwd):
    # Create a new user entity in the "users_db" namespace
    key = client.key('User', namespace='users_db')
    user_entity = datastore.Entity(key=key)

    salt = os.urandom(16)
    pwd = pwd.encode('utf-8')
    hashed_password = hashlib.pbkdf2_hmac('sha256', pwd, salt, 100000)

    user_entity.update({
        'user_id': user_id,
        'hashed_pwd': hashed_password.hex(),
        'salt': salt.hex(),
    })

    # Save the user entity
    client.put(user_entity)
    print(f"New user added with ID: {user_entity.key.id}")


def create_and_insert_character():
    # Create a new character entity in the "characters_db" namespace
    key = client.key('Character', namespace='characters_db')
    character_entity = datastore.Entity(key=key)

    character_entity.update({
        'name': 'Eragon',
        'description': 'Dragon Rider',
        'origin': 'Alagaësia'
    })

    # Save the character entity
    client.put(character_entity)
    print(f"New character added with ID: {character_entity.key.id}")


# Execute the functions
create_and_insert_user("test@gmail.com", "123456")
# create_and_insert_character()

