from google.cloud import datastore

from .get_data import *

def delete_all_entities(kind_name, namespace_name):
    client = datastore.Client.from_service_account_json('../ysong-chat-845e43a6c55b.json')

    # Create a query to fetch all entities of the given kind and namespace
    query = client.query(kind=kind_name, namespace=namespace_name)
    entities = list(query.fetch())

    # Delete each entity
    for entity in entities:
        client.delete(entity.key)

    print(f"Deleted {len(entities)} entities of kind '{kind_name}' from namespace '{namespace_name}'")


# Delete all entities of the kinds "User" and "Character" from the specified namespaces
# delete_all_entities("User", "users_db")
# delete_all_entities("Character", "characters_db")

# delete_account_via_email will delete entities in User and Character datastore.
def delete_account_via_email(datastore_client, user_id): # this is email actually.
    query = datastore_client.query(kind='User', namespace='users_db')
    query.add_filter('user_id', '=', user_id)

    users = list(query.fetch(limit=1))
    if not users or len(users) == 0:
        return False

    character = get_character_by_email(datastore_client, user_id)
    if character is not None:
        datastore_client.delete(character.key)

    datastore_client.delete(users[0].key)
    return True
