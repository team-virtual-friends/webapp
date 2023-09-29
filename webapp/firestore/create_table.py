from google.cloud import datastore

# Initialize client
client = datastore.Client.from_service_account_json('../ysong-chat-845e43a6c55b.json')


def create_and_insert_user():
    # Create a new user entity in the "users_db" namespace
    key = client.key('User', namespace='users_db')
    user_entity = datastore.Entity(key=key)

    user_entity.update({
        'first_name': 'John',
        'last_name': 'Doe',
        'age': 30,
        'email': 'john.doe@example.com'
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
create_and_insert_user()
create_and_insert_character()

