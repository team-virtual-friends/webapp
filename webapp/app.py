import os
from flask import Flask, render_template, redirect, url_for, request, flash, render_template_string
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import EqualTo

from google.cloud import bigquery, storage
from google.cloud.exceptions import Conflict
from datetime import datetime
from google.oauth2 import service_account
import logging
import concurrent.futures
import re
import hashlib
import requests



app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

logger = logging.getLogger('gunicorn.error')

unity_gcs_bucket = "vf-unity-data"
unity_gcs_folders = [
    "20230929234931-f904591-b33afab9", # UI changes.
    "20230930001651-f904591-31e10424", # test runtime optimization.
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
    gcsClient = storage.Client(credentials=credentials)
    bucket = gcsClient.get_bucket(bucket_name)

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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Register')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/game', methods=['GET'])
def game():
    # Get the "FriendIndex" parameter from the URL query string
    binary_index = request.args.get("BinaryIndex")
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

        # Construct the BigQuery client
        credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
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
                bigquery.ScalarQueryParameter("name", "STRING", name),
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("date", "TIMESTAMP", date)
            ]
        )

        try:
            client.query(sql, job_config=job_config).result()
            flash("Successfully added to the waitlist!", "success")
        except Conflict:  # Replace with the appropriate exception for duplicate entries
            flash("You're already on the waitlist!", "warning")

        return redirect(url_for('show_flash_message'))

    return render_template('waitlist.html')


# @app.route('/register', methods=['GET', 'POST'])
# def register():
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # if current_user.is_authenticated:
    #     return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return f'Welcome to the dashboard, {current_user.username}!'


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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Here: implement your login logic (e.g., form validation, user authentication, etc.)
        pass  # Remove this line once you add your implementation

    return render_template('login.html')


@app.route('/show_flash_message')
def show_flash_message():
    return render_template('flash_message.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']
        email = request.form['email']
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


        # Construct the BigQuery client
        credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
        credentials = service_account.Credentials.from_service_account_file(credentials_path)

        if credentials:
            # Construct the BigQuery client
            client = bigquery.Client(credentials=credentials)

            # Define the target table using your dataset and table names
            dataset_name = 'virtualfriends'  # Replace with your dataset name
            table_name = 'feedback_table'  # Replace with your table name
            table_id = f"{client.project}.{dataset_name}.{table_name}"

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
                client.query(sql, job_config=job_config).result()
                flash("Thank you for your feedback!", "success")
            except Conflict:  # Replace with the appropriate exception for duplicate entries
                flash("You've already submitted feedback!", "warning")
        else:
            flash("BigQuery credentials not found. Data not submitted.", "danger")

        return redirect(url_for('show_flash_message'))

    flash("Thank you for your feedback!", 'success')

    # Redirect to a page that displays the flash message
    return redirect(url_for('show_flash_message'))



# Create character and save it to firestore.
from google.cloud import datastore
client = datastore.Client.from_service_account_json('ysong-chat-845e43a6c55b.json')


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

@app.route('/create_character', methods=['GET', 'POST'])
def create_character():

    #TODO: Replace with real user email.
    user_email = "test@gmail.com"

    if request.method == 'POST':
        rpm_url = request.form['rpm_url']
        name = request.form['name']
        gender = request.form['gender']
        character_greeting = request.form['character_greeting']
        character_description = request.form['character_description']
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
        key = client.key('Character', namespace='characters_db')
        character_entity = datastore.Entity(key=key)

        character_entity.update({
            'character_id': character_id,
            'rpm_url': rpm_url,
            'name': name,
            'gender': gender,  # Added the gender field
            'character_greeting': character_greeting,
            'character_description': character_description,
            'audio_file_name': audio_file_name,
            'elevanlab_id': elevanlab_id,
            'created_at': datetime.utcnow(),  # Store the current UTC time as the creation timestamp
            'user_email': user_email,
        })

        # Save the character entity
        client.put(character_entity)

        return render_template('character-profile.html', character=character_entity)

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

def get_character_by_id(character_id):
    # Create a query to fetch character by name in the "characters_db" namespace
    query = client.query(kind='Character', namespace='characters_db')
    query.add_filter('character_id', '=', character_id)

    # Fetch the result
    characters = list(query.fetch(limit=1))

    if characters:
        return characters[0]
    else:
        return None

@app.route('/character/<character_id>', methods=['GET'])
def display_character(character_id):
    # character = get_character_by_name(character_name)  # Assuming you've defined this function earlier
    character = get_character_by_id(character_id)  # Assuming you've defined this function earlier
    return render_template('character-profile.html', character=character)

@app.route('/healthz', methods=['GET'])
def healthz():
    return "Healthy", 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=5132)
