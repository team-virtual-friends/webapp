import os
from flask import Flask, render_template, redirect, url_for, request, flash, make_response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import EqualTo
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email
from flask_wtf import FlaskForm

import io, tempfile
from pydub import AudioSegment
from werkzeug.datastructures import FileStorage

from google.cloud import bigquery, storage, datastore
from google.cloud.exceptions import Conflict
from datetime import datetime as dt

from google.oauth2 import service_account
import logging
import concurrent.futures
import re
import hashlib
import requests
import json
import base64

from data_access.get_data import *
from data_access.create_table import create_and_insert_user
from data_access.delete_data import *
from utils import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

logger = logging.getLogger('gunicorn.error')

credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
datastore_client = datastore.Client(credentials=credentials)
bigquery_client = bigquery.Client(credentials=credentials)
gcs_client = storage.Client(credentials=credentials)

specialCharacters = {
    "2bc098d7b8f35d45f86a2f778f5dd89d": "mina",
    "e75d8532c413d425307ef7d42b5ccd94": "einstein",
}

unity_gcs_bucket = "vf-unity-data"
unity_gcs_folders = [
    "20231110005947-456be4d-8c9808f5",
    "20231105171240-3cccaa0-04e46593",
]
unity_index_html_replacements = {
    "href=\"TemplateData/favicon.ico\"": "href=\"{{{{ url_for('static', filename='{folder_name}/TemplateData/favicon.ico') }}}}\"",
    "href=\"TemplateData/style.css\"": "href=\"{{{{ url_for('static', filename='{folder_name}/TemplateData/style.css') }}}}\"",
    "href=\"manifest.webmanifest\"": "href=\"{{{{ url_for('static', filename='{folder_name}/manifest.webmanifest') }}}}\"",
    "navigator.serviceWorker.register(\"ServiceWorker.js\");": "navigator.serviceWorker.register(\"{{{{ url_for('static', filename='{folder_name}/ServiceWorker.js') }}}}\");",
    "var buildUrl = \"Build\";": "var buildUrl = \"{{{{ url_for('static', filename='{folder_name}/Build') }}}}\";",
}

def load_all_unity_builds(bucket_name:str, unity_gcs_folders:set):
    credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    
    bucket = gcs_client.get_bucket(bucket_name)

    static_folder = "./static/"
    static_folder_full_path = os.path.abspath(static_folder)
    templates_folder = "./templates/"
    templates_folder_full_path = os.path.abspath(templates_folder)

    # for folder_path in unity_gcs_folders:
    def load_unity_build(folder_path:str) -> (str, bool):
        if len(folder_path) == 0:
            logger.error("empty folder_path")
            return (folder_path, False)
        local_folder = static_folder_full_path + '/' + folder_path
        if os.path.exists(local_folder) and os.path.isdir(local_folder):
            logger.error(f"local_folder ({local_folder}) already exists")
            return (folder_path, False)
        blobs = bucket.list_blobs(prefix = folder_path)
        for blob in blobs:
            file_name = blob.name[len(folder_path) :]
            local_path = local_folder + file_name
            os.makedirs(os.path.dirname(local_path), exist_ok = True)
            print(f"downloading f{local_path} ...")
            blob.download_to_filename(local_path)

        # scape the index.html.
        with open(f"{static_folder_full_path}/{folder_path}/index.html") as read_file:
            html = read_file.read()
        for k, v in unity_index_html_replacements.items():
            html = html.replace(k, v.format(folder_name=folder_path))
        # move the index.html to templates.
        with open(f"{templates_folder_full_path}/{folder_path}.html", "w") as write_file:
            write_file.write(html)
        return (folder_path, True)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for folder_path in unity_gcs_folders:
            futures.append(executor.submit(load_unity_build, folder_path))

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                print(f"loaded {result[0]} result: {result[1]}")
            except Exception as e:
                print(f"failed to load coroutine result: {e}")

# load unity build data from GCS
print("loading unity builds from GCS: " + "\\".join(unity_gcs_folders))
load_all_unity_builds(unity_gcs_bucket, unity_gcs_folders)

@app.route('/game', methods=['GET'])
def game():
    # Get the "FriendIndex" parameter from the URL query string
    binary_index = request.args.get("binary_index")
    character_id = request.args.get('character_id')
    viewer_id = validate_user_token()
    if viewer_id is None:
        viewer_id = ""

    # Use the "friend_index" variable as needed in your code
    template_name = unity_gcs_folders[int(binary_index)]
    return render_template(f'{template_name}.html', character_id=character_id, viewer_id=viewer_id)  # Pass it to the template

@app.route('/join_waitlist', methods=['GET', 'POST'])
def join_waitlist():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        date = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        # The SQL query to insert data
        sql = """
            INSERT INTO `ysong-chat.virtualfriends.waitlist_table` (name, email, date)
            VALUES (@name, @email, @date)
        """

        # Set the query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("name", "STRING", name),
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("date", "TIMESTAMP", date)
            ]
        )

        try:
            bigquery_client.query(sql, job_config=job_config).result()
            flash("Successfully added to the waitlist!", "success")
        except Conflict:  # Replace with the appropriate exception for duplicate entries
            flash("You're already on the waitlist!", "warning")

        return redirect(url_for('show_flash_message'))

    return render_template('waitlist.html')


class RegistrationForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form

    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Register')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return_json = request.form.get('format') == 'json'

    form = RegistrationForm()
    if form.validate_on_submit():
        created = create_and_insert_user(datastore_client, form.email.data, form.username.data, form.password.data)
        if created:
            if return_json:
                return json.dumps({"name": form.username.data, "user_email": form.email.data})
            return redirect(url_for('login'))
        
        if return_json:
            return jsonify({"error": "username/email exists"}), 404
        return "username/email exists"

    if return_json:
        for field, errors in form.errors.items():
            for error in errors:
                return jsonify({"error": f"{str(field)}: {str(error)}"}), 404
    return render_template('register.html', form=form)

def is_mobile(user_agent):
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'windows phone']
    user_agent = user_agent.lower()
    for keyword in mobile_keywords:
        if re.search(keyword, user_agent):
            return True
    return False

@app.route('/', methods=['GET'])
def home():
    user_agent = request.headers.get('User-Agent')

    if is_mobile(user_agent):
        return render_template('mobile-index.html'), 200
    def get_characters():
        blocklist = ['0611090e6ccc0e08b5668a1a143238ad', 'c9b6b1876c369f35a340f436a426a66e']

        latest_characters  = get_latest_characters(datastore_client, limit=30, blocklist=blocklist)
        for character in latest_characters:
            character_description = get_character_attribute_value_via_gcs(gcs_client, character,
                                                                          "character_description")
            character["character_description"] = character_description

        result = []
        for ch in latest_characters:
            if validate_avatar_url(ch['rpm_url']):
                result.append({
                    'rpm_url': ch['rpm_url'],
                    'user_email': ch['user_email'],
                    'name': ch['name'],
                    'character_id': ch['character_id'],
                    'character_description': ch['character_description'],
                })
        return result

    recommended_characters = get_characters()

    return render_template('index.html', recommended_characters=recommended_characters), 200

@app.route('/test', methods=['GET'])
def test():
    return render_template('index_test.html'), 200


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    return_json = request.form.get('format') == 'json'

    # Get the username and password from the form
    email = request.form.get('email')
    password = request.form.get('password')
    token = gen_user_auth_token(datastore_client, email, password)
    if token is None:
        if return_json:
            return jsonify({"error": "invalid"}), 404
        return "invalid", 404

    character = get_character_by_email(datastore_client, email)
    if character:
        if return_json:
            character_description = get_character_attribute_value_via_gcs(gcs_client, character, "character_description")
            character["character_description"] = character_description
            response = make_response(json.dumps({
                'user_email': character['user_email'],
                'name': character['name'],
                'character_id': character['character_id'],
                'character_description': character['character_description'],
            }))
        else:
            response = make_response(redirect(url_for('display_user', character_id=character['character_id'])))
        response.set_cookie('auth_token', token)
        return response

    if return_json:
        response = make_response(jsonify({}))
    else:
        response = make_response(redirect(url_for('create_character')))
    response.set_cookie('auth_token', token)
    return response

@app.route('/show_flash_message')
def show_flash_message():
    return render_template('flash_message.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']
        email = request.form['email']
        date = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        # Define the target table using your dataset and table names
        dataset_name = 'virtualfriends'  # Replace with your dataset name
        table_name = 'feedback_table'  # Replace with your table name
        table_id = f"{bigquery_client.project}.{dataset_name}.{table_name}"

        # The SQL query to insert data into the 'feedback_table'
        sql = f"""
            INSERT INTO `{table_id}` (feedback, email, date)
            VALUES (@feedback, @email, @date)
        """

        # Set the query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("feedback", "STRING", feedback),
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("date", "TIMESTAMP", date)
            ]
        )

        try:
            bigquery_client.query(sql, job_config=job_config).result()
            flash("Thank you for your feedback!", "success")
        except Conflict:  # Replace with the appropriate exception for duplicate entries
            flash("You've already submitted feedback!", "warning")

        return redirect(url_for('show_flash_message'))

    flash("Thank you for your feedback!", 'success')

    # Redirect to a page that displays the flash message
    return redirect(url_for('show_flash_message'))

def clone_voice(voice_name, voice_description, audio_file):
    url = "https://api.elevenlabs.io/v1/voices/add"
    api_key = "4fb91ffd3e3e3cd35cbf2d19a64fd4e9"  # Hardcoded API Key

    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }

    data = {
        'name': voice_name,
        'description': voice_description
    }

    files = [('files', (audio_file.filename, audio_file.stream, 'audio/mpeg'))]
    response = requests.post(url, headers=headers, data=data, files=files)

    response_json = response.json()  # Parse the JSON content directly
    # TODO: return err if failed.
    voice_id = response_json.get('voice_id', 'N/A')  # Extract the voice_id or default to 'N/A' if not found

    return voice_id

@app.route('/edit_character', methods=['GET', 'POST'])
def edit_character():
    user_email = validate_user_token()
    if user_email is None:
        return redirect(url_for('login'))

    # Fetch the character entity based on character_id
    character_entity = get_character_by_email(datastore_client, user_email)
    if character_entity is None:
        # Handle the case where the character with the given ID doesn't exist
        return "Character not found", 404

    character_description = get_character_attribute_value_via_gcs(gcs_client, character_entity, "character_description")
    character_prompts = get_character_attribute_value_via_gcs(gcs_client, character_entity, "character_prompts")
    character_id = character_entity["character_id"]

    character_entity["character_description"] = character_description
    character_entity["character_prompts"] = character_prompts

    if request.method == 'POST':
        # Handle the form submission for editing character data
        rpm_url = request.form['rpm_url']
        name = request.form['name']
        gender = request.form['gender']
        character_greeting = request.form['character_greeting']
        character_description = request.form['character_description']
        character_prompts = request.form['character_prompts']
        webm_audio_file = request.files['audioFile']

        elevanlab_id = character_entity['elevanlab_id']
        audio_file = None
        if webm_audio_file:
            mp3_bytes = convert_webm_stream_to_mp3(webm_audio_file.read())
            mp3_bytes_io = io.BytesIO(mp3_bytes)
            audio_file = FileStorage(stream=mp3_bytes_io, filename=f'{character_id}.mp3', content_type='application/octet-stream')
            elevanlab_id = ""
            if audio_file:
                elevanlab_id = clone_voice(name, user_email+" "+character_id, audio_file)
            audio_file.close()
        else:
            elevanlab_id = ""

        # Update the character data in the datastore and/or storage
        updated_character = update_character_info(
            datastore_client, gcs_client, character_entity, rpm_url,
            name, gender, character_greeting, character_description, audio_file, elevanlab_id, character_prompts)

        if updated_character:
            return redirect(url_for('display_user', character_id=character_id))

        return "Failed to update character data"

    # Render the form for editing character data with the existing data
    page_config = {
        'action': 'Update',
        'finish': 'Update',
    }
    return render_template('create-character.html', character=character_entity, page_config=page_config)

def convert_webm_stream_to_mp3(webm_stream):
    # Convert WebM stream to AudioSegment
    webm_audio = AudioSegment.from_file(io.BytesIO(webm_stream), format="webm")

    # Export the audio as an MP3 file
    mp3_bytes = webm_audio.export(format="mp3").read()

    return mp3_bytes

@app.route('/create_character', methods=['GET', 'POST'])
def create_character():
    user_email = validate_user_token()
    if user_email is None:
        return redirect(url_for('login'))


    character = get_character_by_email(datastore_client, user_email)
    if character:
        return redirect(url_for('display_user', character_id=character['character_id']))

    print(f"user_email: {user_email}")
    if request.method == 'POST':
        rpm_url = request.form['rpm_url']
        name = request.form['name']
        gender = request.form['gender']
        character_greeting = request.form['character_greeting'].replace('"', '\\"')
        character_description = request.form['character_description'].replace('"', '\\"')
        character_prompts = request.form['character_prompts'].replace('"', '\\"')
        webm_audio_file = request.files['audioFile']

        date = dt.now().strftime('%Y%m%d%H%M%S')

        character_id_string = f"{user_email}_{date}"
        character_id = hashlib.md5(character_id_string.encode()).hexdigest()

        audio_file_name = None
        elevanlab_id = ""
        if webm_audio_file:
            mp3_bytes = convert_webm_stream_to_mp3(webm_audio_file.read())
            mp3_bytes_io = io.BytesIO(mp3_bytes)
            audio_file = FileStorage(stream=mp3_bytes_io, filename=f'{character_id}.txt', content_type='application/octet-stream')
            # Save the audio file (if needed) and get its name
            # For now, I'm just getting the filename
            audio_file_name = audio_file.name if audio_file else None
            # TODO: Store audio file
            elevanlab_id = ""
            if audio_file:
                elevanlab_id = clone_voice(name, user_email+" "+character_id, audio_file)
            audio_file.close()

        # Create a new character entity in the "characters_db" namespace
        key = datastore_client.key('Character', namespace='characters_db')
        character_entity = save_character_info(
            datastore_client, gcs_client, key,
            character_id, rpm_url, name, gender, character_greeting,
            character_description, audio_file_name, elevanlab_id,
            user_email, character_prompts)

        if character_entity:
            return redirect(url_for('display_user', character_id=character_id))

        return "fail to create the character"

    page_config = {
        'action': 'Create',
        'finish': 'Submit',
    }
    character_entity = {}
    return  render_template('create-character.html', character=character_entity, page_config=page_config)


# #Display character
# def get_character_by_name(character_name):
#     # Create a query to fetch character by name in the "characters_db" namespace
#     query = client.query(kind='Character', namespace='characters_db')
#     query.add_filter('name', '=', character_name)
#
#     # Fetch the result
#     characters = list(query.fetch(limit=1))
#
#     if characters:
#         return characters[0]
#     else:
#         return None

@app.route('/character/<character_id>', methods=['GET'])
def display_character(character_id):
    user_agent = request.headers.get('User-Agent')
    if is_mobile(user_agent):
        return render_template('mobile-index.html'), 200

    # character = get_character_by_name(character_name)  # Assuming you've defined this function earlier
    character = get_character_by_id(datastore_client, character_id)  # Assuming you've defined this function earlier
    character_description = get_character_attribute_value_via_gcs(gcs_client, character, "character_description")
    character["character_description"] = character_description

    return render_template('character-profile.html', character=character)

@app.route('/user/<character_id>', methods=['GET'])
def display_user(character_id):
    # character = get_character_by_name(character_name)  # Assuming you've defined this function earlier
    character = get_character_by_id(datastore_client, character_id)  # Assuming you've defined this function earlier
    character_description = get_character_attribute_value_via_gcs(gcs_client, character, "character_description")
    user_email = validate_user_token()
    if character["user_email"] != user_email:
        return redirect(url_for('display_character', character_id=character['character_id']))

    character["character_description"] = character_description
    return render_template('user-profile.html', character=character)

@app.route('/delete/user', methods=['GET'])
def delete_user():
    return_json = request.args.get('format') == 'json'

    user_email = validate_user_token()
    if user_email is None:
        if return_json:
            return jsonify({"error": "unauthorized"}), 500
        return "unauthorized", 500
    if delete_account_via_email(datastore_client, user_email):
        return ""
    if return_json:
        return "failed", 500
    return jsonify({"error": "failed"}), 500

def make_character_list(characters, characterType):
    result = []
    for character in characters:
        if validate_avatar_url(character['rpm_url']):
            character_description = get_character_attribute_value_via_gcs(gcs_client, character, "character_description")
            character["character_description"] = character_description
            profile_picture_path = character.get("profile_picture")
            if profile_picture_path is not None:
                profile_picture_bytes = get_character_attribute_bytes_via_gcs(gcs_client, character, "profile_picture")
                character["profile_picture"] = base64.b64encode(profile_picture_bytes).decode("utf-8")

            result.append({
                'user_email': character['user_email'],
                'name': character['name'],
                'character_id': character['character_id'],
                'character_description': character['character_description'],
                'profile_picture': character.get("profile_picture", ""),
                'recommend_type': characterType,
            })
    return result

@app.route('/search/character/<prefix>', methods=['GET'])
def display_search_results(prefix):
    characters = search_characters_by_prefix(datastore_client, prefix)
    result = make_character_list(characters, "search")
    if request.args.get('format') == 'json':
        return json.dumps(result)
    return render_template('search_character_results.html', characters=result)

@app.route('/recommend', methods=['GET'])
def recommend_users():
    if 'count' in request.args:
        count = int(request.args.get('count'))
    else:
        count = 10

    pinned_characters = [get_character_by_id(datastore_client, character) for character in [
        "2bc098d7b8f35d45f86a2f778f5dd89d", # mina
        "e75d8532c413d425307ef7d42b5ccd94", # einstein
    ]]
    pinned_character_dict = {}
    for character in pinned_characters:
        pinned_character_dict[character["character_id"]] = character
    result = make_character_list(pinned_characters, "pinned")
    
    random_characters = get_random_characters(datastore_client, limit=count)
    random_result = make_character_list(random_characters, "random")

    for ch in random_result:
        characterId = ch['character_id']
        if not characterId in pinned_character_dict:
            result.append(ch)

    return json.dumps(result)

@app.route("/marketplace")
def display_model_marketplace():
    marketplace_models = [
        "mina",
        "einstein",
        "m-00001",
        "m-00002",
        "m-00003",
        "m-00004",
        "m-00005",
        "w-00001",
        "w-00002",
        "w-00003",
        "w-00004",
        "w-00005",
        "w-00006",
        "w-00007",
        "w-00008",
        "w-00009",
        "w-00010",
        "w-00011",
        "w-00012",
        "w-00013",
        "w-00014",
        "w-00015",
        "w-00016",
    ]
    return render_template('model_marketplace.html', model_infos=[{
        'image_url': url_for('static', filename=f'model_marketplace/{marketplace_model}.png'),
        'url': f'vf://blob/{marketplace_model}',
    } for marketplace_model in marketplace_models])

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    return_json = request.args.get('format') == 'json'

    user_email = validate_user_token()
    if user_email is None:
        if return_json:
            return jsonify({"error": "unauthorized"}), 500
        return redirect(url_for('login'))
    
    print(f"user_email: {user_email}")
    character = get_character_by_email(datastore_client, user_email)
    if character is None:
        if return_json:
            return jsonify({})
        return make_response(redirect(url_for('create_character')))
    character_id = character.get('character_id', '')

    # Ensure character_id is present
    if len(character_id) == 0:
        return jsonify({"error": "character_id is required"}), 400

    character_entity = get_character_by_id(datastore_client, character_id)
    name = character_entity.get('name', 'Assistant')

    # The SQL query to fetch chat history
    sql = """
    WITH MaxTimestamps AS (
        SELECT chat_session_id, MAX(timestamp) AS max_timestamp
        FROM `ysong-chat.virtualfriends.chat_history`
        WHERE character_id = @character_id
        GROUP BY chat_session_id
    )

    SELECT ch.*
    FROM `ysong-chat.virtualfriends.chat_history` AS ch
    JOIN MaxTimestamps AS mt ON ch.chat_session_id = mt.chat_session_id AND ch.timestamp = mt.max_timestamp
    WHERE ch.character_id = @character_id
    ORDER BY ch.timestamp DESC
    LIMIT 30;
    """

    # Set the query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("character_id", "STRING", character_id)
        ]
    )

    try:
        results = bigquery_client.query(sql, job_config=job_config).result()

        chat_history_data = []
        for row in results:
            row_dict = {}
            for key, value in row.items():
                row_dict[key] = value
            print(row_dict)

            cleaned_chat_history = re.sub(r'user:\s*\n', '', row['chat_history'].replace("A:", "\n" + name + ":"))
            cleaned_chat_history = re.sub(r'user:', r'\nUser:', cleaned_chat_history)

            row_dict['chat_history'] =cleaned_chat_history
            chat_history_data.append(row_dict)
        
        if return_json:
            return jsonify(chat_history_data)

        # Return the rendered HTML with the chat history data
        return render_template('chat_history.html', chat_history=chat_history_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/healthz', methods=['GET'])
def healthz():
    return "Healthy", 200

if __name__ == "__main__":
    app.run(debug=True, port=5558)
