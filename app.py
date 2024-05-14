from sqlite3 import IntegrityError
from flask import Flask, request, url_for, redirect, render_template, session, flash
from datetime import timedelta, datetime
import base64
import utils, os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import db, validators
import datetime
import os
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


app = Flask(__name__)
app.secret_key = "findwhatyouloveandletitKILLYOU"
app.permanent_session_lifetime = timedelta(days=5)
connection = db.connect_to_database()
limiter = Limiter(
    app=app, key_func=get_remote_address, default_limits=["50 per minute"])

app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = r'C:\Users\DINESH\Dropbox\PC\Desktop\social\Social-Media-WebApp\connect-app\Upload'

@app.route("/", methods=["GET", "POST"])
def home():
    check_login = session.get("logged_in", False)
    check_register = session.get("registered", False)
    if check_login and check_register:
        if request.method == "POST":
            if "username" in request.form and request.form["username"]:
                userName = request.form["username"]
                user = db.get_user_with_posts(connection, userName)
                if not user:
                    flash("The user you search for does not exist !", "danger")
                    return redirect(url_for("home"))
                else:
                    return render_template("profile.html", user=user)
            elif "description" in request.form and request.form["description"]:
                image_for_post = request.files["image"]
                if not image_for_post or image_for_post.filename == "":
                    flash("Nothing was Selected, please Choose something", "danger")
                    return render_template("home.html")

                if not validators.allowed_file(
                    image_for_post.filename
                ) or not validators.allowed_file_size(image_for_post):
                    flash("Invalid File is Uploaded", "danger")
                    return render_template("home.html")
                description_for_post = request.form["description"]
                image_data = base64.b64encode(image_for_post.read()).decode("utf-8")
                image_ext = image_for_post.filename.split(".")[1]
                user_id = session["user_id"]
                db.add_post(
                    connection,
                    user_id,
                    description_for_post,
                    image_data,
                    image_ext,
                    datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                )
                flash("Post Created Successfully!!", "success")
            else:
                post_id = request.form["post_id"]
                db.delete_post_by_id(
                    connection,
                    post_id,
                )
        posts = db.get_all_posts(connection)
        return render_template("home.html", posts=posts)
    elif check_register and not check_login:
        flash("Please Log in First", "info")
        return redirect(url_for("login"))
    else:
        flash("Please Register First", "info")
        return redirect(url_for("register"))


@app.route("/profile/<user_id>", methods=["GET", "POST"])
def profile(user_id):

    check_login = session.get("logged_in", False)
    check_register = session.get("registered", False)
    if check_register and not check_login:
        return redirect(url_for("login"))
    elif not check_register and not check_login:
        return redirect(url_for("register"))
    else :
        username = db.get_user_by_user_id(connection, user_id)[1]
        user = db.get_user_with_posts(connection, username)
        return render_template("profile.html", user=user)


@app.route("/display_post/<post_id>", methods=["GET", "POST"])
def display_post(post_id):
    check_login = session.get("logged_in", False)
    check_register = session.get("registered", False)
    if check_register and not check_login:
        return redirect(url_for("login"))
    elif not check_register and not check_login:
        return redirect(url_for("register"))
    post = db.get_post_by_post_id(connection, post_id)
    print(post_id)
    comments = db.get_comments_by_post_id(connection, post_id)
    if request.method == "GET":
        return render_template("display_post.html", post=post, comments=comments)
    elif request.method == "POST":
        user_id = session["user_id"]
        if "comment" in request.form and request.form["comment"]:
            comment_content = request.form["comment"]
            db.add_comment_to_db(
                connection,
                user_id,
                comment_content,
                post_id,
                datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            )
        else:
            comment_id = request.form["comment_id"]
            db.delete_comment_by_id(
                connection,
                comment_id,
            )
    return redirect(url_for("display_post", post_id=post_id))


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # File upload handling
        if "profile_photo" in request.files:
            profile_photo = request.files["profile_photo"]
            if profile_photo.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)
            if profile_photo and validators.allowed_file(profile_photo.filename):
                filename = secure_filename(profile_photo.filename)
                profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            else:
                flash('Invalid file type', 'danger')
                return redirect(request.url)
        
        if not utils.is_strong_password(password):
            flash("Sorry You Entered a weak Password Please Choose a stronger one", "danger")
            return render_template("register.html")

        token = db.get_user_by_username(connection, username)

        if not token:
            hashedPassword = utils.hash_password(password)
            db.add_user(
                connection, username, hashedPassword, profile_image_path  # Add profile image path here
            )
            session["username"] = username
            session["logged_in"] = False
            session["registered"] = True
            session["user_id"] = db.get_user_by_username(connection, username)[0]
            flash("Account Created Successfully!!", "success")
            return redirect(url_for("login"))
        else:
            flash("User already exists!", "danger")
            session["registered"] = True
            return redirect(url_for("login"))

    return render_template("register.html")


def get_user_with_posts(connection, username):
    user = get_user_by_username(connection, username)

    if user is None:
        return None

    cursor = connection.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    if user is None:
        return None

    user_id = user[0]
    profile_image = user[4]  # Assuming profile_image is in the 5th column

    cursor.execute("SELECT * FROM POSTS WHERE user_id = ?", (user_id,))
    posts = []
    for row in cursor.fetchall():
        post = {
            "post_id": row[0],
            "user_id": row[1],
            "description": row[3],
            "image_data": row[4],
            "image_ext": row[5],
            "date": row[2],
            "username": username,
        }
        posts.append(post)

    user_with_posts = {
        "user_id": user_id,
        "username": username,
        "posts": posts,
        "profile_image": profile_image,  # Adding profile image to the user object
    }
    return user_with_posts



# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = db.get_user_by_username(connection, username)
        if user:
            real_password = user[2]
            if utils.is_password_match(password, real_password):
                session["logged_in"] = True
                session["username"] = username
                session["user_id"] = user[0]
                session["admin"] = user[3]
                flash("Welcome " + username, "success")
                return redirect(url_for("home"))
            else:
                flash("Incorrect Password. Please try again.", "danger")
        else:
            flash("User does not exist. Please register!", "danger")
            return redirect(url_for("register"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("logged_in", None)
    flash("Logged Out Successfully!", "success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    db.init_users(connection)
    db.init_posts(connection)
    db.init_comments(connection)
    app.run(debug=True)

