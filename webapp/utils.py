from flask import request, render_template

from data_access.get_data import validate_token

def get_token_from_cookie():
    token = request.cookies.get('auth_token')
    return token

def requires_token():
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract the token from the cookie or request
            token = get_token_from_cookie()  # Implement this function as needed
            (verified, email) = validate_token(token)
            if verified:
                return func(email, *args, **kwargs)
            else:
                return render_template('login.html')

        return wrapper

    return decorator