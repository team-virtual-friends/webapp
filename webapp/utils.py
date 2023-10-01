from flask import request, render_template

from data_access.get_data import validate_token

def validate_user_token():
    token = request.cookies.get('auth_token')
    (verified, user_email) = validate_token(token)
    if verified:
        return user_email
    return None
