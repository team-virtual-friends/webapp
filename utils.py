import re

from flask import request, render_template

from data_access.get_data import validate_token

def validate_user_token():
    token = request.cookies.get('auth_token')
    (verified, user_email) = validate_token(token)
    if verified:
        return user_email
    return None

def validate_avatar_url(url):
    rpm_regex = r"https:\/\/models\.readyplayer\.me\/[0-9a-z]+\.glb"
    matches = re.finditer(rpm_regex, url, re.MULTILINE)
    if any(matches):
        return True
    
    blob_download_prefix = "vf://blob/"
    if url.startswith(blob_download_prefix):
        return True

    avaturn_regex = r"https:\/\/api\.avaturn\.me\/[a-z0-9\/\-]+"
    matches = re.finditer(avaturn_regex, url, re.MULTILINE)
    if any(matches):
        return True
    
    return False
