""" Server functionality for app  """
import os
from flask import Flask, session, request, render_template, redirect, flash
from model import connect_to_db, User, Author, Fav_Author

from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined

# need secret key in order to use sessions
# note need to run secrets file in order to set secret key
app.secret_key = os.environ["FLASK_SECRET_KEY"]


@app.route("/")
def show_homepage():
    return render_template("homepage.html")


@app.route("/login", methods=["GET"])
def show_login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    # check to see if user and password in database
    # if they are, they good
    # otherwise, flash a message and
    # redirect("/login")
    pass


@app.route("/sign-up", methods=["GET"])
def show_signup():
    return render_template("signup.html")


@app.route("/sign-up", methods=["POST"])
def signup():
    # check to see if email already in database
    # if it is, flash a message and 
    # redirect("/signup")
    # otherwise add email and provided info to database
    # then log them in (add them to the session, I guess)
    # and redirect to the user profile page
    pass


@app.route("/user/<user_id>")
def show_profile(user_id):
    user = User.query.get(user_id)
    return render_template("user_info.html", user=user)

if __name__ == "__main__":
    app.debug = True
    app.jinja_env.auto_reload = app.debug
    connect_to_db(app)
    DebugToolbarExtension(app)
    app.run(host="0.0.0.0")
