from flask import Flask, render_template, request, session, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate  # New: Flask-Migrate for migrations
import json
from datetime import datetime
import math

# Load config
with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server = "True"
app = Flask(__name__)
app.secret_key = 'super-secret-key'
csrf = CSRFProtect(app)

# Database configuration
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # New: Initialize Flask-Migrate

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)  # Ensure this matches the database schema

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        # print("hash=",self.password_hash)
        # print("pass-",password)
        return check_password_hash(self.password_hash, password)


# Existing Models
class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    meg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20), nullable=True)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(20), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    tagline = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20), nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route("/")
@login_required
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    posts = posts[(page - 1) * int(params['no_of_posts']):(page - 1) * int(params['no_of_posts']) + int(
        params['no_of_posts'])]
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Debugging: Check if the user is already authenticated
    print("Is user authenticated?", current_user.is_authenticated)
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # Redirect to home if already logged in

    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')

        # Debugging: Check username and password
        # print("Username:", username)
        # print("Password:", password)

        user = User.query.filter_by(username=username).first()
        # if user:
            # Debugging: Check password validation
            # print("Password hash in database:", user.password_hash)
            # print("Password validation result:", user.check_password(password))

        # Authenticate user
        if user and user.check_password(password):
            login_user(user)  # Log in the user
            print("User logged in successfully.")

            # Handle redirection to 'next' page
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # Avoid open redirects
                return redirect(next_page)
            return redirect(url_for('home'))  # Default to home page
        else:
            flash('Invalid username or password', 'error')
            print("Invalid credentials.")

    return render_template('login.html', params=params)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    print('Logged out successfully.', 'success')
    return redirect(url_for('login'))


@app.route("/dashboard")
@login_required
def dashboard():
    posts = Posts.query.filter_by().all()
    return render_template('dashboard.html', params=params, posts=posts)


@app.route("/about")
@login_required
def about():
    return render_template('about.html', params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])
@login_required
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route("/contact", methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contacts(name=name, email=email, phone_num=phone, meg=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()

    return render_template('contact.html', params=params)


# Add new user (you should create a proper registration system)
@app.route('/init_admin')
def init_admin():
    if User.query.filter_by(username=params['admin_user']).first() is None:
        user = User(username='Aryan')
        user.set_password('abcdefgh')
        db.session.add(user)
        db.session.commit()
        flash('Admin user created successfully', 'success')
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
