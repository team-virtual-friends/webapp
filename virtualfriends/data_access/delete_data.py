from google.cloud import datastore


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
delete_all_entities("User", "users_db")
delete_all_entities("Character", "characters_db")