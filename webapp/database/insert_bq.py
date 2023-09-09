from google.cloud import bigquery
from google.oauth2 import service_account
import os


from google.cloud import bigquery


# # Create a client for the Google Text-to-Speech API
credentials_path = os.path.expanduser('../ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
client = bigquery.Client(credentials=credentials)


# The SQL query to insert data
sql = """
    INSERT INTO `ysong-chat.virtualfriends.waitlist_table` (name, email, date)
    VALUES (@name, @email, @date)
"""

# Set the query parameters
job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("name", "STRING", "ss"),
        bigquery.ScalarQueryParameter("email", "STRING", "ss@ss"),
        bigquery.ScalarQueryParameter("date", "TIMESTAMP", None)
    ]
)

client.query(sql, job_config=job_config).result()
