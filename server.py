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
goodreads_key = os.environ["GOODREADS_API_KEY"]
google_books_key = os.environ["GOOGLE_BOOKS_API_KEY"]


def get_author_goodreads_id(author_name):
    """ Given author name, returns Goodreads ID associated with name, if it exists.
    Otherwise returns None."""
    payload = {"key": goodreads_key}
    url = "https://www.goodreads.com/api/author_url/{}".format(author_name)
    goodreads_id = None

    response = requests.get(url, params=payload)

    if response.status_code == 200:
        tree = ET.fromstring(response.content)
        goodreads_id = tree[1].attrib["id"]

    return goodreads_id


@app.route("/")
def show_homepage():
    return render_template("homepage.html")


@app.route("/search")
def show_search():
    series = Series.query.all()
    return render_template("search.html", series=series)


@app.route("/search", methods=["POST"])
def search():
    author = request.form.get("author")
    series_name = request.form.get("series")
    print(series_name)

    if author and series_name:
        flash("Please enter only one!")
        return redirect("/search")
    elif author:
        payload = {"q": "inauthor:" + author,
                   "langRestrict": "en",
                   "orderBy": "newest",
                   "printType": "books",
                   "key": google_books_key
                   }
        # if I want to limit fields I should mess around with requests to see what I get
        # also I should probably limit how many results I get back. I don't need to comb through
        # 400 + results... right?
        response = requests.get("https://www.googleapis.com/books/v1/volumes", params=payload)

        if response.status_code == 200:
            results = response.json()  # returns a very complicated dictionary
            next_book = results["items"][0]["volumeInfo"]

            print(next_book["title"], next_book["publishedDate"])
            if "search_history" in session:
                session["search_history"].append((author, next_book["title"], next_book["publishedDate"]))
            flash("Something happened!")
            return redirect("/search")

        else:
            flash("Something went wrong :(")
            return redirect("/search")
    elif series_name:
        series = Series.query.filter_by(series_name=series_name).first()
        if series.goodreads_id:
            payload = {"key": goodreads_key,
                       "id": series.goodreads_id}
            response = requests.get(" https://www.goodreads.com/series/show/", params=payload)
            xml_root = ET.fromstring(response.content)
            #so, first, I need to know how many books are in this series
            #note I can chain find/findalls together to make my thought process clearer
            series_length = xml_root.find("series").find("primary_work_count").text
            series_works = list(xml_root.find("series").find("series_works"))  # a list of all the books in said series
            # what if I could sort the roots by publication order?
            # woud make traversing a lot easier
            # how do I want to deal when no user_position is given?
            # probably do some handling and make it so that None is now a string which makes sense
            # I can edit the tree, after all.
            # lst2 = sorted(series_works, key=lambda work: work.find("user_position").text, reverse=True)
            # print(lst2)
            title = None
            published = None
            for work in series_works:
                if work[1].text == series_length:
                    title = work.find("work").find("original_title").text
                    published = work.find("work").find("original_publication_year").text

            print(title, published)
            if "search_history" in session:
                session["search_history"].append((series_name, title, published))
            # Need to add to search history as well!
            flash("Something happened!")
            return redirect("/search")

    else:
        flash("Please enter an author or series")
        return redirect("/search")


@app.route("/adv-search")
def show_adv_search():
    return render_template("adv-search.html")


@app.route("/by-author", methods=["POST"])
def search_by_author():
    author_name = request.form.get("author")
    # need to make sure we actually got an input from author? 
    author = Author.query.filter_by(author_name=author_name).first()

    if author:  # author is in database
        if author.goodreads_id:
            payload = {"key": goodreads_key, "id": author.goodreads_id}
            response = requests.get("https://www.goodreads.com/series/list", params=payload)

            if response.status_code == 200:
                tree = ET.fromstring(response.content)

            else:  # could not make a response, or something happened
                pass

        else:
            actual_id = get_author_goodreads_id(author_name)
            if actual_id:
                author.goodreads_id = actual_id

    else:  # author is not in database
        actual_id = get_author_goodreads_id(author_name)
        if actual_id:
            db.session.add(Author(author_name=author_name, goodreads_id=actual_id))
            # then search, I guess? IDK how I want to display this yet
        else:
            pass

    # check to see if author in database
    # if so, use goodreads id to get list of series to show you
    # if not, get goodreads id to search
    # after getting series, show them to user, who can then pick which one to search
    # then we add series to database (to make it easier in the future)
    # and show them the results (possibly factor out code in normal search to here)
    # if no id exists, tell user so
    pass


@app.route("/by-book", methods=["POST"])
def search_by_book():
    title = request.form.get("title")
    # need to check that the author actually exists?

    payload = {"q": title, "key": goodreads_key}

    response = requests.get("https://www.goodreads.com/search/index.xml", params=payload)

    if response.status_code == 200:  # got a response
        tree = ET.fromstring(response.content)
    else:  # tell the user that there was an error
        pass
    # so, to search by book:
    # go to goodreads and get a list of books by title
    # goodreads returns the top twenty
    # show the series associated with each book
    # let the user pick which series they want to search
    # then let them search
    # if nothing comes back, or if the user can't find the series in the first twenty books, tell the user so 


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
        session["search_history"] = []
        flash("Successfully logged in!")
        return redirect("/user/{}".format(user.user_id))

    else:
        flash("Incorrect username/password")
        return redirect("/login")


@app.route("/logout")
def logout():
    if "user_id" in session:
        del session["user_id"]
        del session["search_history"]
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
                goodreads_id = get_author_goodreads_id(author_name)

                db.session.add(Author(author_name=author_name, goodreads_id=goodreads_id))
                db.session.commit()

                author_id = Author.query.filter_by(author_name=author_name).first().author_id
                db.session.add(Fav_Author(author_id=author_id, user_id=user_id))

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

    if new_series:  # if I can't figure out a good way to handle this, I'm going to have to remove this functionality
        for series_name in new_series:
            series = Series.query.filter_by(series_name=series_name).first()
            if series:

                if Fav_Series.query.filter_by(series_id=series.series_id, user_id=user_id):
                    flash("You already liked {}!".format(series.series_name))

                else:
                    db.session.add(Fav_Series(series_id=series.series_id, user_id=user_id))

    db.session.commit()
    flash("Series successfully updated")
    return redirect("/user/{}".format(user_id))


@app.route("/author/<author_id>")
def show_author_info(author_id):
    author = Author.query.get(author_id)

    if author.goodreads_id is None:
        author.goodreads_id = get_author_goodreads_id(author.author_name)
        # query goodreads to see if there is an id
        # if so, set it
        # otherwise, don't do anything

    if author.goodreads_id:
        payload = {"id": author.goodreads_id, "key": goodreads_key}
        response = requests.get("https://www.goodreads.com/author/show/", params=payload)
        # if response was successfully made
        tree = ET.fromstring(response.content)
        author_info = tree.find("author")
        # info to display: total works, gender, list of series, list of works
        pass

    else:
        # display something else
        pass

    return render_template("author_info.html", author=author)


@app.route("/series/<series_id>")
def show_series_info(series_id):
    series = Series.query.get(series_id)
    # since all series have goodread ids now
    # can send a request to goodreads to get info!
    if series.goodreads_id:
        pass

    return render_template("series_info.html", series=series)


if __name__ == "__main__":
    app.debug = True
    app.jinja_env.auto_reload = app.debug
    connect_to_db(app)
    DebugToolbarExtension(app)
    app.run(host="0.0.0.0")
