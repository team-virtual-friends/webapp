from google.cloud import datastore
import hashlib
import datetime
import jwt

secret_key = "chilloutmix_ni64"

# Initialize the Datastore client
# client = datastore.Client.from_service_account_json('../webapp/ysong-chat-845e43a6c55b.json')


def get_character_by_name(client, character_name):
    # Create a query to fetch character by name in the "characters_db" namespace
    query = client.query(kind='Character', namespace='characters_db')
    query.add_filter('name', '=', character_name)

    # Fetch the result
    characters = list(query.fetch(limit=1))

    if characters:
        return characters[0]
    return None

def validate_user(client, user_id, pwd):
    query = client.query(kind='User', namespace='users_db')
    query.add_filter('user_id', '=', user_id)

    users = list(query.fetch(limit=1))
    if not users or len(users) == 0:
        return False

    user = users[0]
    stored_hashed_pwd = user['hashed_pwd']
    stored_salt = bytes.fromhex(user['salt'])

    # Hash the user's entered password using the retrieved salt
    hashed_password_attempt = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), stored_salt, 100000)

    # Convert the computed hash to hexadecimal for comparison
    hashed_password_attempt_hex = hashed_password_attempt.hex()
    return hashed_password_attempt_hex == stored_hashed_pwd
    
def gen_user_auth_token(client, user_id, pwd):
    if validate_user(client, user_id, pwd):
        # Payload (claims) containing user information
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=24)  # Token expiration time
        }

        # Generate a token
        return jwt.encode(payload, secret_key, algorithm="HS256")
    return None

def validate_token(token) -> (bool, str):
    if token is None or len(token) == 0:
        return (False, "")
    try:
        decoded_payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        expiry = decoded_payload['exp']

        expiry_datetime = datetime.datetime.utcfromtimestamp(expiry)
        current_time = datetime.datetime.utcnow()
        if expiry_datetime > current_time:
            return (True, decoded_payload['user_id'])
        return (False, "")
    except jwt.ExpiredSignatureError:
        # Token has expired
        return (False, "")
    except jwt.InvalidTokenError:
        # Token is invalid (e.g., tampered with)
        return (False, "")

# if __name__ == '__main__':
#     token = gen_user_auth_token(client, "test@gmail.com", "123456")
#     print(token)
#     print(validate_token(token))
