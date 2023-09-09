from google.cloud import bigquery
from google.oauth2 import service_account
import os


from google.cloud import bigquery


# # Create a client for the Google Text-to-Speech API
credentials_path = os.path.expanduser('../ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = bigquery.Client(credentials=credentials)


# Define your dataset and table names
dataset_name = 'virtualfriends'
table_name = 'waitlist_table'

# Define your table schema
schema = [
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("email", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("date", "TIMESTAMP", mode="REQUIRED")
]

# Create the table
dataset_ref = client.dataset(dataset_name)
table_ref = dataset_ref.table(table_name)
table = bigquery.Table(table_ref, schema=schema)
table = client.create_table(table)

print(f"Created table {table.full_table_id} with name, email, and date fields")
