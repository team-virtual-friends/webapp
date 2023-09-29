from google.cloud import datastore

# Initialize the Datastore client
client = datastore.Client.from_service_account_json('../ysong-chat-845e43a6c55b.json')


def get_character_by_name(character_name):
    # Create a query to fetch character by name in the "characters_db" namespace
    query = client.query(kind='Character', namespace='characters_db')
    query.add_filter('name', '=', character_name)

    # Fetch the result
    characters = list(query.fetch(limit=1))

    if characters:
        return characters[0]
    else:
        return None

# Example Usage:
character = get_character_by_name("sss")
if character:
    print(character)
else:
    print("Character not found.")