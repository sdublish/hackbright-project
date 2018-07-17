""" Server functionality for app  """
import os
import requests
import xml.etree.ElementTree as ET

from flask import Flask, session, request, render_template, redirect, flash, jsonify
from model import connect_to_db, User, Author, Fav_Author, Series, Fav_Series, db

from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined

app.secret_key = os.environ["FLASK_SECRET_KEY"]
goodreads_key = os.environ["GOODREADS_API_KEY"]
google_books_key = os.environ["GOOGLE_BOOKS_API_KEY"]


def get_author_goodreads_info(author_name):
    """ Given author name, returns (goodreads_id, goodreads_name), if it exists.
    Otherwise returns (None, None)."""
    payload = {"key": goodreads_key}
    url = "https://www.goodreads.com/api/author_url/{}".format(author_name)
    goodreads_id = None
    goodreads_name = None

    response = requests.get(url, params=payload)

    if response.status_code == 200:
        tree = ET.fromstring(response.content)
        if tree.find("author"):
            goodreads_id = tree.find("author").attrib["id"]
            goodreads_name = tree.find("author").find("name").text
            # if this is a dictionary, can't I solve this with get?
            # well, not if the dictionary doesn't exist in the first place?
            # Need to check on this

    return (goodreads_id, goodreads_name)


def sort_series(series_list):
    """ Given a list of series nodes based off a response from the Goodreads API,
    returns all the series  with sharing the lowest user_position value. If there is
    no series, returns an empty dictionary. If there are only series with no user_position
    value, returns a dictionary containing all unique series. Lowest user_position
    value which will be returned is 1. Result format:
    { series_id : series_title}"""
    by_user_position = {}

    for series in series_list:
        user_position = series.find("user_position").text
        series_id = series.find("series").find("id").text
        series_name = series.find("series").find("title").text.strip()

        if user_position in by_user_position:
            by_user_position[user_position][series_id] = series_name

        else:
            by_user_position[user_position] = {series_id: series_name}

    if len(by_user_position) == 0:
        return {}

    elif len(by_user_position) == 1:
        # i could also just get the first thing in the list of values...
        return by_user_position.popitem()[1]

    else:
        smallest_user_position = min(key for key in by_user_position if key is not None and key >= "1")
        return by_user_position[smallest_user_position]


def get_series_list_by_author(author_id):
    payload = {"key": goodreads_key, "id": author_id}
    response = requests.get("https://www.goodreads.com/series/list", params=payload)

    if response.status_code == 200:
        tree = ET.fromstring(response.content)
        if tree.find("series_works"):
            all_series = list(tree.find("series_works"))
            return sort_series(all_series)

        else:  # no series found
            return {}

    else:  # could not make a response, or something happened
        return None


def get_last_book_of_series(series_name, series_id):
    payload = {"key": goodreads_key, "id": series_id}
    response = requests.get(" https://www.goodreads.com/series/show/", params=payload)
    # also need to do some checks to make sure everything is working well with the API
    tree = ET.fromstring(response.content)
    series_length = tree.find("series").find("primary_work_count").text
    # series length should be an integer, so I don't need to worry about working with strings, I think
    series_works = list(tree.find("series").find("series_works"))  # a list of all the books in said series
    by_user_position = {}
    for work in series_works:
        user_position = work.find("user_position").text
        # user position, at least in a series, seems to be pretty unique
        by_user_position[user_position] = work

    title = None
    published = None

    while title is None and series_length >= "1":
        work = by_user_position[series_length]  # maybe do get here so i don't get a key error
        title = work.find("work").find("original_title").text
        published = work.find("work").find("original_publication_year").text
        series_length = str(int(series_length) - 1)

    # I could do a check here seeing if title is none, and replacing it with something else

    print(title, published)
    if "search_history" in session:
        session["search_history"].append((series_name, title, published))

    return {'title': title, 'published': published}

    # things I need to do: if no publication date is provided, get publication date from Google Books
    # I need to do a decent amount of data validation here


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

            next_book_id = results["items"][0]["id"]

            payload_2 = {"key": google_books_key}
            url = "https://www.googleapis.com/books/v1/volumes/{}".format(next_book_id)

            r2 = requests.get(url, params=payload_2)
            # can do another check here to see if request went okay
            results_2 = r2.json()
            published_date = results_2["volumeInfo"]["publishedDate"]

            # seems like the best way to get thww correct publication info is to go straight to the book. Multiple API calls, yay!
            # Also, need to do more data validation stuff here.

            print(next_book["title"], published_date)

            if "search_history" in session:
                session["search_history"].append((author, next_book["title"], published_date))

            flash("Something happened!")
            return redirect("/search")

        else:
            flash("Something went wrong")
            return redirect("/search")

    elif series_name:
        series = Series.query.filter_by(series_name=series_name).first()
        if series.goodreads_id:
            get_last_book_of_series(series_name, series.goodreads_id)
            # how do I want to do the search for the publication date?
            # do I simply want to do an author search and go from there?

            flash("Something happened!")
            return redirect("/search")

        else:
            flash("Something went wrong")
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
        title = "Series by {}".format(author_name)
        if author.goodreads_id:  # if author has goodreads id
                series_info = get_series_list_by_author(author.goodreads_id)
                if series_info is not None:  # if we get results
                    # also I probably should add search results to search history as well
                    return render_template("series_results.html", series=series_info, title=title)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again")
                    return redirect("/adv-search")

        else:  # author does not have a goodreads id
            actual_id = get_author_goodreads_info(author_name)[0]

            if actual_id:  # if you get a goodreads id
                author.goodreads_id = actual_id
                db.session.commit()

                series_info = get_series_list_by_author(actual_id)
                if series_info is not None:  # if everything worked

                    return render_template("series_results.html", series=series_info, title=title)

                else:  # error occured/returned None
                    flash("An error occured. Please try again")
                    return redirect("/adv-search")

            else:
                flash("I'm sorry, we can't find info on this author in our external resources. Sorry about that!")
                return redirect("/adv-search")

    else:  # author is not in database
        # can you unpack a tuple? Might make sense here
        actual_info = get_author_goodreads_info(author_name)

        if actual_info[0]:
            possible_author = Author.query.filter_by(goodreads_id=actual_info[0]).first()

            if possible_author:  # if there was a typo that goodreads handled
                series_info = get_series_list_by_author(possible_author.goodreads_id)

                if series_info is not None:  # if we get results
                    flash("Showing results for {} instead of {}".format(possible_author.author_name, author_name))
                    title = "Series by {}".format(possible_author.author_name)
                    return render_template("series_results.html", series=series_info, title=title)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again")
                    return redirect("/adv-search")
            else:  # author is not in database
                db.session.add(Author(author_name=actual_info[1], goodreads_id=actual_info[0]))
                db.session.commit()
                series_info = get_series_list_by_author(actual_info[0])

                if series_info is not None:  # if we get results
                    if author_name != actual_info[1]:
                        flash("Showing results for {} instead of {}".format(actual_info[1], author_name))
                    title = "Series by {}".format(actual_info[1])
                    return render_template("series_results.html", series=series_info, title=title)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again")
                    return redirect("/adv-search")

        else:  # if no author id is returned
            flash("Could not find an author with that name. Please try again.")
            return redirect("/adv-search")


@app.route("/series-result.json", methods=["POST"])
def show_series_results():
    series_id = request.form.get("id")
    series_name = request.form.get("name")

    if series_id and series_name:  # if there is a series id and name
        results = get_last_book_of_series(series_name, series_id)

        if not Series.query.filter_by(goodreads_id=series_id).first():  # if series is not in database
            db.session.add(Series(goodreads_id=series_id, series_name=series_name))
            db.session.commit()

        return jsonify(results)

    else:  # should think if I really want this redirect here
        flash("An error occured. Please try again.")
        return redirect("/adv-search")


@app.route("/by-book", methods=["POST"])
def search_by_book():
    title = request.form.get("title")

    payload = {"q": title, "key": goodreads_key}

    response = requests.get("https://www.goodreads.com/search/index.xml", params=payload)

    if response.status_code == 200:  # got a response
        tree = ET.fromstring(response.content)
        # probably should put a check in here to see if we get results
        # so should check to see if results actually come in (tree.find(search).find(results))
        books = list(tree.find("search").find("results"))
        book_info = []
        for book in books:
            # I need to show: book title, book author, and book id
            book_title = book.find("best_book").find("title").text.strip()
            book_author = book.find("best_book").find("author").find("name").text.strip()
            book_id = book.find("id").text

            book_info.append((book_title, book_author, book_id))

        return render_template("book_results.html", query=title, books=book_info)

    else:  # tell the user that there was an error
        flash("Something went wrong. Please try again!")
        return redirect("/adv-search")


@app.route("/book-series", methods=["POST"])
def series_by_books():
    # could definitely do unpacking here, if I wanted to
    book_info = request.form.get("book").split("||")
    book_id = book_info[0].strip()
    book_name = book_info[1].strip()

    title = "Series That {} Belong To".format(book_name)
    if book_id:
        payload = {"key": goodreads_key}
        url = "https://www.goodreads.com/work/{}/series".format(book_id)
        response = requests.get(url, params=payload)

        if response.status_code == 200:
            tree = ET.fromstring(response.content)
            series = {}
            if tree.find("series_works"):  # if the book is part of a series
                all_series = list(tree.find("series_works"))
                series = sort_series(all_series)

            return render_template("series_results.html", series=series, title=title)

        else:  # something went wrong with the request
            flash("Something went wrong. Please try again.")
            return redirect("/adv-search")

    else:  # for some reason we don't have a book id
        flash("Something went wrong.")
        return redirect("/adv-search")


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

    else:  # don't think I need this check if I have one built into template creation?
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
            session["search_history"] = []

            flash("You are now logged in, {}!".format(fname))

            return redirect("/user/{}".format(user_id))

        else:
            flash("Please input values into all fields!")
            return redirect("/sign-up")


@app.route("/user/<user_id>")
def show_profile(user_id):
    user = User.query.get(user_id)
    fav_series_id = [s.series_id for s in Fav_Series.query.filter_by(user_id=user_id).all()]
    series = Series.query.filter(db.not_(Series.series_id.in_(fav_series_id))).all()
    return render_template("user_info.html", user=user, series=series)


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
    unfav_authors = request.form.getlist("author-remove")
    new_authors = request.form.get("new-author").strip().splitlines()

    if unfav_authors:
        for author_id in unfav_authors:
            author = Fav_Author.query.filter_by(author_id=author_id, user_id=user_id).first()
            if author:
                db.session.delete(author)
                flash("Successfully removed {}".format(author.author.author_name))

    if new_authors:
        for author_name in new_authors:
            author = Author.query.filter_by(author_name=author_name).first()

            if author:  # if author in database
                if Fav_Author.query.filter_by(author_id=author.author_id, user_id=user_id).first():
                    flash("You already liked {}!".format(author.author_name))

                else:
                    db.session.add(Fav_Author(author_id=author.author_id, user_id=user_id))
                    flash("Successfully added {}".format(author_name))
            else:  # if author is NOT in database
                goodreads_info = get_author_goodreads_info(author_name)

                if author_name != goodreads_info[1]:  # name entered and name returned from goodreads do not match (indicates typo)
                    flash("Could not find {}. Did you mean {}?".format(author_name, goodreads_info[1]))

                else:  # author is definitely NOT in database
                    db.session.add(Author(author_name=goodreads_info[1], goodreads_id=goodreads_info[0]))
                    db.session.commit()

                    author_id = Author.query.filter_by(author_name=author_name).first().author_id
                    db.session.add(Fav_Author(author_id=author_id, user_id=user_id))
                    flash("Successfully added {}".format(author_name))

    db.session.commit()
    return redirect("/user/{}".format(user_id))


@app.route("/update-fav-author.json", methods=["POST"])
def update_fav_author():
    user_id = request.form.get("user_id")
    author_id = request.form.get("author_id")

    if user_id and author_id:
        if Fav_Author.query.filter_by(author_id=author_id, user_id=user_id).first():
            return jsonify({"result": "You have already favorited this author!"})

        else:
            db.session.add(Fav_Author(author_id=author_id, user_id=user_id))
            db.session.commit()
            return jsonify({"result": "New favorite author added!"})
    else:
        return jsonify({"result": "Something went wrong."})


@app.route("/update-series", methods=["POST"])
def update_series():
    user_id = request.form.get("user_id")
    unfav_series = request.form.getlist("series-remove")
    new_series = request.form.getlist("series-add")

    if unfav_series:
        for series_id in unfav_series:
            series = Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first()
            if series:
                db.session.delete(series)
                flash("Successfully removed {}".format(series.series.series_name))

    if new_series:
        for series_id in new_series:
            series = Series.query.get(series_id)
            if Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first():
                flash("You already liked {}!".format(series.series_name))

            else:
                db.session.add(Fav_Series(series_id=series_id, user_id=user_id))

    # maybe figure out I want to handle if the series check fails later...

    db.session.commit()
    flash("Series successfully updated")
    return redirect("/user/{}".format(user_id))


@app.route("/update-fav-series.json", methods=["POST"])
def update_fav_series():
    user_id = request.form.get("user_id")
    series_id = request.form.get("series_id")

    if user_id and series_id:
        if Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first():
            return jsonify({"result": "You have already favorited this series!"})

        else:
            db.session.add(Fav_Series(series_id=series_id, user_id=user_id))
            db.session.commit()
            return jsonify({"result": "New favorite series added!"})
    else:
        return jsonify({"result": "Something went wrong"})


@app.route("/author/<author_id>")
def show_author_info(author_id):
    author = Author.query.get(author_id)

    if author.goodreads_id is None:
        # author.goodreads_id = get_author_goodreads_info(author.authoruthor_name)[0]
        # db.session.commit()
        pass

    if author.goodreads_id:
        payload = {"id": author.goodreads_id, "key": goodreads_key}
        response = requests.get("https://www.goodreads.com/author/show/", params=payload)
        # if response was successfully made
        tree = ET.fromstring(response.content)
        author_info = tree.find("author")
        # info to display: total works, gender, list of series, list of works
        return render_template("author_info.html", author=author)

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
