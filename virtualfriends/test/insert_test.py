from google.cloud import bigquery
import os
from google.oauth2 import service_account


# Load the BigQuery credentials and create a BigQuery client
credentials_path = os.path.expanduser('../ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = bigquery.Client(credentials=credentials)

# Define your dataset and table names
dataset_name = 'virtualfriends'
table_name = 'chat_history'

def log_chat_history(user_id, user_ip, character_id, chat_history, timestamp):
    try:
        # Create a reference to your dataset and table
        dataset_ref = client.dataset(dataset_name)
        table_ref = dataset_ref.table(table_name)
        table = client.get_table(table_ref)

        # Insert a new row into the table
        row_to_insert = (user_id, user_ip, character_id, chat_history, timestamp)

        client.insert_rows(table, [row_to_insert])

        print("Data inserted successfully")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage:
log_chat_history("user123", "192.168.1.1", "mina", "Hello, world!", "2023-09-20T12:00:00")