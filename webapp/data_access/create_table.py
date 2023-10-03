from google.cloud import datastore
import os
import hashlib

# Initialize client
# client = datastore.Client.from_service_account_json('../webapp/ysong-chat-845e43a6c55b.json')


def create_and_insert_user(datastore_client, user_id, username, pwd):
    # Check if a user with the same username or user_id already exists
    query1 = datastore_client.query(kind='User', namespace='users_db')
    query1.add_filter('username', '=', username)

    query2 = datastore_client.query(kind='User', namespace='users_db')
    query2.add_filter('user_id', '=', user_id)

    results_query1 = list(query1.fetch(limit=1))
    results_query2 = list(query2.fetch(limit=1))

    # Check if either of the queries found a match
    if results_query1 or results_query2:
        # A user with the same username or user_id already exists
        return False

    # If no matching user exists, proceed to create and insert the new user entity
    key = datastore_client.key('User', namespace='users_db')
    user_entity = datastore.Entity(key=key)

    salt = os.urandom(16)
    pwd = pwd.encode('utf-8')
    hashed_password = hashlib.pbkdf2_hmac('sha256', pwd, salt, 100000)

    user_entity.update({
        'user_id': user_id,
        'username': username,
        'hashed_pwd': hashed_password.hex(),
        'salt': salt.hex(),
    })

    # Save the user entity
    datastore_client.put(user_entity)
    print(f"New user added with ID: {user_entity.key.id}")
    return True  # Successfully created and inserted the user entity


def create_and_insert_character(datastore_client):
    # Create a new character entity in the "characters_db" namespace
    key = datastore_client.key('Character', namespace='characters_db')
    character_entity = datastore.Entity(key=key)

    character_entity.update({
        'name': 'Eragon',
        'description': 'Dragon Rider',
        'origin': 'Alagaësia'
    })

    # Save the character entity
    datastore_client.put(character_entity)
    print(f"New character added with ID: {character_entity.key.id}")


# Execute the functions
# create_and_insert_user("test@gmail.com", "test", "123456")
# create_and_insert_character()
