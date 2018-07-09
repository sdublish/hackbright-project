""" Server functionality for app  """

from flask import Flask, session, request, render_template, redirect
from model import connect_to_db

from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined

# need secret key in order to use sessions
app.secret_key = "ekdoteencharpanchche"


@app.route("/")
def show_homepage():
    return render_template("homepage.html")


@app.route("/login", methods=["GET"])
def show_login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    pass


@app.route("/sign-up", methods=["GET"])
def show_signup():
    return render_template("signup.html")


@app.route("/sign-up", methods=["POST"])
def signup():
    pass

if __name__ == "__main__":
    app.debug = True
    app.jinja_env.auto_reload = app.debug
    connect_to_db(app)
    DebugToolbarExtension(app)
    app.run(host="0.0.0.0")
