from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Set up BigQuery client
credentials_path = os.path.expanduser('../ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = bigquery.Client(credentials=credentials)

dataset_name = 'virtualfriends'

# Create a function to create a BigQuery table
def create_table(table_name, schema):
    dataset_ref = client.dataset(dataset_name)
    table_ref = dataset_ref.table(table_name)
    table = bigquery.Table(table_ref, schema=schema)

    try:
        table = client.create_table(table)
        print(f"Created table {table.full_table_id}")
    except Exception as e:
        print(f"An error occurred: {e}")


# Create latency_log table
latency_log_schema = [
    bigquery.SchemaField("env", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("user_id", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("user_ip", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("character_id", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("latency_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("latency_value", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE")
]

create_table('latency_log', latency_log_schema)
