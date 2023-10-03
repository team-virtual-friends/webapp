import os
from flask import Flask, render_template, redirect, url_for, request, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import EqualTo
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email
from flask_wtf import FlaskForm


from google.cloud import bigquery, storage, datastore
from google.cloud.exceptions import Conflict
from datetime import datetime
from google.oauth2 import service_account
import logging
import concurrent.futures
import re
import hashlib
import requests

from data_access.get_data import gen_user_auth_token, get_character_by_id, get_character_by_email, save_character_info, update_character_info, get_character_attribute_value_via_gcs
from data_access.create_table import create_and_insert_user
from utils import validate_user_token

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

logger = logging.getLogger('gunicorn.error')

credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
credentials = service_account.Credentials.from_service_account_file(credentials_path)
datastore_client = datastore.Client(credentials=credentials)
bigquery_client = bigquery.Client(credentials=credentials)
gcs_client = storage.Client(credentials=credentials)

unity_gcs_bucket = "vf-unity-data"
unity_gcs_folders = [
    "20231002205259-ce829a6-a2f82cb1", # desktop.
    "20231002222116-ce829a6-841aa765", # mobile - no Input Text box.
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
            return (folder_path, False)
        local_folder = static_folder_full_path + '/' + folder_path
        if os.path.exists(local_folder) and os.path.isdir(local_folder):
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

    # Use the "friend_index" variable as needed in your code
    template_name = unity_gcs_folders[int(binary_index)]
    return render_template(f'{template_name}.html', character_id=character_id)  # Pass it to the template

@app.route('/join_waitlist', methods=['GET', 'POST'])
def join_waitlist():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    form = RegistrationForm()
    if form.validate_on_submit():
        created = create_and_insert_user(datastore_client, form.email.data, form.username.data, form.password.data)
        if created:
            return redirect(url_for('login'))
        return "username/email exists"
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

    # if current_user.is_authenticated:
    #     return redirect(url_for('dashboard'))
    # else:
    return render_template('index.html'), 200

@app.route('/test', methods=['GET'])
def test():
    return render_template('index.html'), 200


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    # Get the username and password from the form
    email = request.form.get('email')
    password = request.form.get('password')
    token = gen_user_auth_token(datastore_client, email, password)
    if token is None:
        return "invalid", 404

    character = get_character_by_email(datastore_client, email)
    if character:
        response = make_response(redirect(url_for('display_user', character_id=character['character_id'])))
        response.set_cookie('auth_token', token)
        return response

    response = make_response(render_template('create-character.html'))
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
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

@app.route('/edit_character/<character_id>', methods=['GET', 'POST'])
def edit_character(character_id):
    user_email = validate_user_token()
    if user_email is None:
        return redirect(url_for('login'))

    # Fetch the character entity based on character_id
    character_entity = get_character_by_id(datastore_client, character_id)
    character_description = get_character_attribute_value_via_gcs(gcs_client, character_entity, "character_description")
    character_prompts = get_character_attribute_value_via_gcs(gcs_client, character_entity, "character_prompts")

    character_entity["character_description"] = character_description
    character_entity["character_prompts"] = character_prompts

    if character_entity is None:
        # Handle the case where the character with the given ID doesn't exist
        return "Character not found", 404

    if request.method == 'POST':
        # Handle the form submission for editing character data
        rpm_url = request.form['rpm_url']
        name = request.form['name']
        gender = request.form['gender']
        character_greeting = request.form['character_greeting']
        character_description = request.form['character_description']
        character_prompts = request.form['character_prompts']
        audio_file = request.files['audioFile']

        # # TODO: Store audio file
        elevanlab_id = character_entity['elevanlab_id']
        if audio_file:
            elevanlab_id = clone_voice(name, user_email+" "+character_id, audio_file)

        # Update the character data in the datastore and/or storage
        updated_character = update_character_info(
            datastore_client, gcs_client, character_entity, rpm_url,
            name, gender, character_greeting, character_description, audio_file, elevanlab_id, character_prompts)

        if updated_character:
            return redirect(url_for('display_user', character_id=character_id))

        return "Failed to update character data"

    # Render the form for editing character data with the existing data
    return render_template('edit-character.html', character=character_entity)


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
        character_greeting = request.form['character_greeting']
        character_description = request.form['character_description']
        character_prompts = request.form['character_prompts']
        audio_file = request.files['audioFile']

        character_id_string = f"{user_email}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        character_id = hashlib.md5(character_id_string.encode()).hexdigest()

        # Save the audio file (if needed) and get its name
        # For now, I'm just getting the filename
        audio_file_name = audio_file.filename if audio_file else None
        # TODO: Store audio file
        elevanlab_id = ""
        if audio_file:
            elevanlab_id = clone_voice(name, user_email+" "+character_id, audio_file)

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

    return render_template('create-character.html')


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
    character["character_description"] = character_description
    return render_template('user-profile.html', character=character)

@app.route('/healthz', methods=['GET'])
def healthz():
    return "Healthy", 200

if __name__ == "__main__":
    app.run(debug=True, port=5235)
