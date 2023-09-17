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


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

logger = logging.getLogger('gunicorn.error')

unity_gcs_bucket = "vf-unity-data"
unity_gcs_folders = set([
    "20230915195202-542cded-fc82bb4c",
])

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
    friend_index = request.args.get('FriendIndex')

    # Use the "friend_index" variable as needed in your code
    return render_template('game.html', FriendIndex=friend_index)  # Pass it to the template

@app.route('/game_blob', methods=['GET'])
def game_blob():
    return render_template("test.html")

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

        return redirect(url_for('join_waitlist'))

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


@app.route('/', methods=['GET'])
def home():
    # if current_user.is_authenticated:
    #     return redirect(url_for('dashboard'))
    # else:
    return render_template('index.html'), 200


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Here: implement your login logic (e.g., form validation, user authentication, etc.)
        pass  # Remove this line once you add your implementation

    return render_template('login.html')

@app.route('/healthz', methods=['GET'])
def healthz():
    return "Healthy", 200

def load_all_unity_builds(bucket_name:str, unity_gcs_folders:set, local:str):
    credentials_path = os.path.expanduser('ysong-chat-845e43a6c55b.json')
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    gcsClient = storage.Client(credentials=credentials)
    bucket = gcsClient.get_bucket(bucket_name)

    full_local = os.path.abspath(local)
    print(full_local)
    for folder_path in unity_gcs_folders:
        blobs = bucket.list_blobs(prefix = folder_path)
        for blob in blobs:
            local_path = full_local + folder_path + blob.name[len(folder_path) :]
            print(local_path)
            print(os.path.dirname(local_path))
            os.makedirs(os.path.dirname(local_path), exist_ok = True)
            blob.download_to_filename(local_path)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    # load unity build data from GCS
    logger.info("loading unity builds from GCS: " + "\\".join(unity_gcs_folders))
    load_all_unity_builds(unity_gcs_bucket, unity_gcs_folders, "./templates/")

    app.run(debug=True, port=5125)
