""" Server functionality for app  """
import os
import requests
import xml.etree.ElementTree as ET

from flask import Flask, session, request, render_template, redirect, flash
from model import connect_to_db, User, Author, Fav_Author, Series, Fav_Series, db

from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined

# note need to run secrets file in order to set secret key
app.secret_key = os.environ["FLASK_SECRET_KEY"]


@app.route("/")
def show_homepage():
    return render_template("homepage.html")


@app.route("/search")
def show_search():
    return render_template("search.html")


@app.route("/search", methods=["POST"])
def search():
    author = request.form.get("author")
    series_name = request.form.get("series")

    if author and series_name:
        flash("Please enter only one!")
        return redirect("/search")
    elif author:
        payload = {"q": "inauthor:" + author,
                   "langRestrict": "en",
                   "orderBy": "newest",
                   "printType": "books",
                   "key": os.environ["GOOGLE_BOOKS_API_KEY"]
                   }

        response = requests.get("https://www.googleapis.com/books/v1/volumes", params=payload)
        # if response = 200, we can turn into JSON, I believe
        results = response.json()
        next_book = results["items"][0]["volumeInfo"]
        print(next_book)
        # search google books for author and get back info
        flash("Something happened!")
        return redirect("/search")
    elif series_name:
        series = Series.query.filter_by(series_name=series_name)
        if series:
            payload = {"key": os.environ["GOODREADS_API_KEY"],
                       "id": series.goodreads_id}
            response = request.get(" https://www.goodreads.com/series/show/", params=payload)
            # create a tree based off xml
            # get a list of nodes which contain the info about the books
            # go backwards through list: last book should be most recent
            # if book doesn't have date, go to Google books to get date
            # otherwise use date in goodreads
        # check to see if series is in database. If it is, request info about that series and handle.
        # If it isn't... we're going to do something very roundabout...
        payload = {}
        # search goodreads for series and get back info
        pass
    else:
        flash("Please enter an author or series")
        return redirect("/search")


@app.route("/login", methods=["GET"])
def show_login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email, password=password).first()

    if user:  # if the email and password match what's in the database
        session["user_id"] = user.user_id
        flash("Successfully logged in!")
        return redirect("/user/{}".format(user.user_id))

    else:
        flash("Incorrect username/password")
        return redirect("/login")


@app.route("/logout")
def logout():
    if "user_id" in session:
        del session["user_id"]
        flash("Logged out!")

    else:  # don't think I need this check if I have one built into tmeplate creation?
        flash("Not logged in!")

    return redirect("/")


@app.route("/sign-up", methods=["GET"])
def show_signup():
    return render_template("signup.html")


@app.route("/sign-up", methods=["POST"])
def signup():
    email = request.form.get("email")

    if User.query.filter_by(email=email).first():  # if email exists in database
        flash("Email already exists. Please try again.")
        return redirect("/sign-up")

    else:
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        password = request.form.get("password")

        # not sure if this check is necessary... or constructed properly
        if fname and lname and email and password:
            db.session.add(User(email=email, fname=fname, lname=lname,
                                password=password))

            db.session.commit()

            flash("New user successfully added!")

            user_id = User.query.filter_by(email=email).first().user_id
            session["user_id"] = user_id

            flash("You are now logged in, {}!".format(fname))

            return redirect("/user/{}".format(user_id))

        else:
            flash("Please input values into all fields!")
            return redirect("/sign-up")


@app.route("/user/<user_id>")
def show_profile(user_id):
    user = User.query.get(user_id)
    return render_template("user_info.html", user=user)


@app.route("/update-profile", methods=["POST"])
def update_profile():
    user_id = request.form.get("user_id")
    age = request.form.get("age")
    zipcode = request.form.get("zipcode")
    fav_book = request.form.get("fav-book")

    user = User.query.get(user_id)

    if age:
        user.age = age
    if zipcode:
        user.zipcode = zipcode
    if fav_book:
        user.fav_book = fav_book

    db.session.commit()

    flash("Info successfully updated!")
    return redirect("/user/{}".format(user_id))


@app.route("/update-authors", methods=["POST"])
def update_authors():
    user_id = request.form.get("user_id")
    unfav_authors = request.form.get("author-remove")
    new_authors = request.form.get("new-author").strip().splitlines()

    if unfav_authors:
        for author_id in unfav_authors:
            author = Fav_Author.query.filter_by(author_id=author_id, user_id=user_id).first()
            if author:
                db.session.delete(author)

    if new_authors:
        for author_name in new_authors:
            author = Author.query.filter_by(author_name=author_name).first()

            if author:
                if Fav_Author.query.filter_by(author_id=author.author_id, user_id=user_id):
                    flash("You already liked {}!".format(author.author_name))

                else:
                    db.session.add(Fav_Author(author_id=author.author_id, user_id=user_id))
            else:
                # need to add author to database
                pass

    db.session.commit()
    flash("Authors successfully updated")
    return redirect("/user/{}".format(user_id))


@app.route("/update-series", methods=["POST"])
def update_series():
    user_id = request.form.get("user_id")
    unfav_series = request.form.get("series-remove")
    new_series = request.form.get("new-series").strip().splitlines()

    if unfav_series:
        for series_id in unfav_series:
            series = Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first()
            if series:
                db.session.delete(series)

    if new_series:
        for series_name in new_series:
            series = Series.query.filter_by(series_name=series_name).first()
            if series:

                if Fav_Series.query.filter_by(series_id=series.series_id, user_id=user_id):
                    flash("You already liked {}!".format(series.series_name))

                else:
                    db.session.add(Fav_Series(series_id=series.series_id, user_id=user_id))
            else:
                # need to add series to database
                pass

    db.session.commit()
    flash("Series successfully updated")
    return redirect("/user/{}".format(user_id))

if __name__ == "__main__":
    app.debug = True
    app.jinja_env.auto_reload = app.debug
    connect_to_db(app)
    DebugToolbarExtension(app)
    app.run(host="0.0.0.0")
