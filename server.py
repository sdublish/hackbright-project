""" Server functionality for app  """
import os
import requests
import wikipedia

from flask import Flask, session, request, render_template, redirect, flash, jsonify
from flask_mail import Mail, Message
from rauth import OAuth1Service, OAuth1Session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from google_util import get_pub_date_with_book_id, google_books_key, get_pub_date_with_title
from server_util import strip_tags, convert_string_to_datetime
from goodreads_util import (ET, goodreads_key, get_author_goodreads_info, get_series_list_by_author,
                            sort_series, get_last_book_of_series, get_info_for_work)
from model import connect_to_db, User, Author, Fav_Author, Series, Fav_Series, db

from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined

mail_settings = {
    "MAIL_SERVER": "smtp.gmail.com",
    "MAIL_PORT": 465,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ["APP_EMAIL"],
    "MAIL_DEFAULT_SENDER": os.environ["APP_EMAIL"],
    "MAIL_PASSWORD": os.environ["APP_EMAIL_PASSWORD"]
}

app.config.update(mail_settings)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
mail = Mail(app)


goodreads = OAuth1Service(
    consumer_key=goodreads_key,
    consumer_secret=os.environ["GOODREADS_API_SECRET"],
    name='goodreads',
    request_token_url='https://www.goodreads.com/oauth/request_token',
    authorize_url='https://www.goodreads.com/oauth/authorize',
    access_token_url='https://www.goodreads.com/oauth/access_token',
    base_url='https://www.goodreads.com/'
    )

request_token, request_token_secret = goodreads.get_request_token(header_auth=True)
authorizaton_url = goodreads.get_authorize_url(request_token)

# dictionary in format of (days, what option is called)
timeframes = {183: "Next Six Months", 365: "Next Year", 730: "In Two Years",
              0: "First Book Found"}
no_cover_img = "https://d298d76i4rjz9u.cloudfront.net/assets/no-cover-art-found-c49d11316f42a2f9ba45f46cfe0335bbbc75d97c797ac185cdb397a6a7aad78c.jpg"
no_results_img = "http://sendmeglobal.net/images/404.png"


@app.route("/")
def show_homepage():
    """ Renders homepage """
    return render_template("homepage.html")


@app.route("/search")
def show_search():
    """ Renders search page """
    series = Series.query.all()
    fav_auth = None
    fav_series = None

    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        fav_auth = user.fav_authors
        fav_series = user.fav_series

    return render_template("search.html", series=series, tfs=timeframes, fav_auths=fav_auth, fav_series=fav_series)


@app.route("/search.json", methods=["POST"])
def search_json():
    author = request.form.get("author")
    series_id = request.form.get("series")
    timeframe = int(request.form.get("timeframe"))
    tf_str = timeframes[timeframe]

    date = request.form.get("date")
    date_str = " ".join(date.split()[1:])
    py_date = datetime.strptime(date_str, "%b %d %Y")
    td = timedelta(days=timeframe)

    if author:  # considering moving this to google_util, even though functionality isn't reused
        payload = {"q": "inauthor:" + author,
                   "langRestrict": "en",
                   "orderBy": "newest",
                   "printType": "books",
                   "key": google_books_key
                   }

        response = requests.get("https://www.googleapis.com/books/v1/volumes", params=payload)

        if response.status_code == 200:
            results = response.json()
            # can clean up the code here
            next_book = results["items"][0]["volumeInfo"]
            next_book_cover = no_cover_img

            if results["items"][0]["volumeInfo"].get("imageLinks"):
                next_book_cover = results["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]

            next_book_id = results["items"][0]["id"]

            published_date = get_pub_date_with_book_id(next_book_id)
            # if error, return jsonify({status:error})
            # what if this returns an error? What do I want to do?
            pdate = convert_string_to_datetime(published_date)

            most_recent = (next_book["title"], published_date, next_book_cover)
            result = most_recent

            if td and not (py_date <= pdate <= py_date + td):
                if pdate < py_date:
                    result = (None, None, no_results_img)
                else:
                    for work in results["items"][1:]:
                        date2 = get_pub_date_with_book_id(work["id"])
                        pdate2 = convert_string_to_datetime(date2)
                        next_book_cover2 = no_cover_img

                        if work["volumeInfo"].get("imageLinks"):
                            next_book_cover2 = work["volumeInfo"]["imageLinks"]["thumbnail"]

                        if pdate2 < py_date:
                            result = (None, None, no_results_img)
                            break
                        elif py_date <= pdate2 <= py_date + td:
                            result = (work["volumeInfo"]["title"], date2, next_book_cover2)
                            break

            if "search_history" in session:
                search = (date, tf_str, author, most_recent, result)
                # this looks redundant, but if I try to modify the session value directly
                # it doesn't update, so it has to be like this
                s_history = session["search_history"]
                s_history.append(search)
                session["search_history"] = s_history

            return jsonify({"results": result, "most_recent": most_recent})

        # need to figure out how I want to handle if the API throws an error

    else:  # if series is being searched
        # need to modify this to handle what would happen if it returns an error
        series = Series.query.get(series_id)
        results = get_last_book_of_series(series.series_name, series.goodreads_id, py_date, td)

        if "search_history" in session:
            search = (date, tf_str, series.series_name, results["most_recent"], results["results"])
            # this looks redundant, but if I try to modify the session value directly
            # it doesn't update, so it has to be like this
            s_history = session["search_history"]
            s_history.append(search)
            session["search_history"] = s_history

        return jsonify(results)


@app.route("/email-info.json", methods=["POST"])
def email_info_to_user():
    """Sends email to user if user logged in. Returns json indicating if email was sent successfully"""
    user = User.query.get(session.get("user_id"))
    result = request.form.get("result")
    title = request.form.get("title")

    if user:
        msg = Message(subject=title, html=result, recipients=[user.email])
        mail.send(msg)
        return jsonify({"status": "Email sent! Look for bibliofindapp@gmail.com in your inbox."})

    else:
        return jsonify({"status": "An error occurred. Make sure you're signed in."})


@app.route("/adv-search")
def show_adv_search():
    """ Renders advanced search page """
    return render_template("adv-search.html")


@app.route("/by-author", methods=["POST"])
def search_by_author():
    author_name = request.form.get("author")
    author = Author.query.filter_by(author_name=author_name).first()

    if author:  # author is in database
        title = "Series by {}".format(author_name)
        if author.goodreads_id:  # if author has goodreads id
                series_info = get_series_list_by_author(author.goodreads_id)

                if series_info is not None:  # if we get results
                    return render_template("series_results.html", series=series_info, title=title, tfs=timeframes)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again", "danger")
                    return redirect("/adv-search")

        else:  # author does not have a goodreads id
            actual_id = get_author_goodreads_info(author_name)[0]

            if actual_id:  # if you get a goodreads id
                author.goodreads_id = actual_id
                db.session.commit()

                series_info = get_series_list_by_author(actual_id)

                if series_info is not None:  # if everything worked
                    return render_template("series_results.html", series=series_info, title=title, tfs=timeframes)

                else:  # error occured/returned None
                    flash("An error occured. Please try again", "danger")
                    return redirect("/adv-search")

            else:
                flash("I'm sorry, we can't find info on this author in our external resources. Sorry about that!", "warning")
                return redirect("/adv-search")

    else:  # author is not in database
        # can you unpack a tuple? Might make sense here
        actual_info = get_author_goodreads_info(author_name)

        if actual_info[0]:
            possible_author = Author.query.filter_by(goodreads_id=actual_info[0]).first()

            if possible_author:  # if there was a typo that goodreads handled
                series_info = get_series_list_by_author(possible_author.goodreads_id)

                if series_info is not None:  # if we get results
                    flash("Showing results for {} instead of {}".format(possible_author.author_name, author_name), "info")
                    title = "Series by {}".format(possible_author.author_name)
                    return render_template("series_results.html", series=series_info, title=title, tfs=timeframes)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again", "danger")
                    return redirect("/adv-search")

            else:  # author is not in database
                db.session.add(Author(author_name=actual_info[1], goodreads_id=actual_info[0]))
                db.session.commit()
                series_info = get_series_list_by_author(actual_info[0])

                if series_info is not None:  # if we get results
                    if author_name != actual_info[1]:
                        flash("Showing results for {} instead of {}".format(actual_info[1], author_name), "info")

                    title = "Series by {}".format(actual_info[1])
                    return render_template("series_results.html", series=series_info, title=title, tfs=timeframes)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again", "danger")
                    return redirect("/adv-search")

        else:  # if no author id is returned
            flash("Could not find an author with that name. Please try again.", "warning")
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
            book_cover = book.find("best_book").find("image_url").text

            book_info.append((book_title, book_author, book_id, book_cover))

        return render_template("book_results.html", query=title, books=book_info)

    else:  # tell the user that there was an error
        flash("Something went wrong. Please try again!", "danger")
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

            return render_template("series_results.html", series=series, title=title, tfs=timeframes)

        else:  # something went wrong with the request
            flash("Something went wrong. Please try again.", "danger")
            return redirect("/adv-search")

    else:  # for some reason we don't have a book id
        flash("Something went wrong.", "danger")
        return redirect("/adv-search")


@app.route("/series-result.json", methods=["POST"])
def show_series_results():
    series_id = request.form.get("id")
    series_name = request.form.get("name")

    date = request.form.get("date")
    date_str = " ".join(date.split()[1:])
    py_date = datetime.strptime(date_str, "%b %d %Y")

    timeframe = int(request.form.get("timeframe"))
    tf_str = timeframes[timeframe]
    td = timedelta(days=timeframe)

    if series_id and series_name:  # if there is a series id and name
        results = get_last_book_of_series(series_name, series_id, py_date, td)

        if "search_history" in session:
            search = (date, tf_str, series_name, results["most_recent"], results["results"])
            # this looks redundant, but if I try to modify the session value directly
            # it doesn't update, so it has to be like this
            s_history = session["search_history"]
            s_history.append(search)
            session["search_history"] = s_history

        if not Series.query.filter_by(goodreads_id=series_id).first():  # if series is not in database
            db.session.add(Series(goodreads_id=series_id, series_name=series_name))
            db.session.commit()

        return jsonify(results)

    else:
        return jsonify({"status": "error"})


@app.route("/login", methods=["GET"])
def show_login():
    """ Renders login page """
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
    # if the email and password match what's in the database
        session["user_id"] = user.user_id
        session["search_history"] = []
        flash("Successfully logged in!", "success")
        return redirect("/user/{}".format(user.user_id))

    else:
        flash("Incorrect username/password", "warning")
        return redirect("/login")


@app.route("/logout")
def logout():
    """ Logs out user """
    if "user_id" in session:
        del session["user_id"]
        del session["search_history"]
        flash("Logged out!", "success")

    else:  # safety check just in case someome tries to access manually
        flash("You can't log out if you're not logged in!", "warning")

    return redirect("/")


@app.route("/sign-up", methods=["GET"])
def show_signup():
    """ Renders sign-up page """
    return render_template("signup.html")


@app.route("/sign-up", methods=["POST"])
def signup():
    email = request.form.get("email")

    if User.query.filter_by(email=email).first():  # if email exists in database
        flash("Email already exists. Please try again.", "warning")
        return redirect("/sign-up")

    else:
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        password = request.form.get("password")

        # is there a way to prevent a user from signing up as a string of spaces??
        if fname and lname and email and password:
            db.session.add(User(email=email, fname=fname, lname=lname,
                                password=generate_password_hash(password)))

            db.session.commit()

            flash("New user successfully added!", "success")

            user_id = User.query.filter_by(email=email).first().user_id
            session["user_id"] = user_id
            session["search_history"] = []

            flash("You are now logged in, {}!".format(fname), "info")

            return redirect("/user/{}".format(user_id))

        else:
            flash("Please input values into all fields!", "warning")
            return redirect("/sign-up")


@app.route("/user/<user_id>")
def show_profile(user_id):
    """ Renders user profile page """
    user = User.query.get(user_id)

    if user:
        # you know, I could probably change this query so it only returns the series_id...
        fav_series_id = [s.series_id for s in Fav_Series.query.filter_by(user_id=user_id).all()]
        series = Series.query.filter(db.not_(Series.series_id.in_(fav_series_id))).all()
        return render_template("user_info.html", user=user, series=series)

    else:
        flash("User does not exist", "danger")
        if "user_id" in session:
            return redirect("/user/{}".format(session["user_id"]))
        else:
            return redirect("/")


@app.route("/goodreads-oauth")
def goodreads_oauth():
    """ Provides url needed for Goodreads OAuth """
    return redirect(authorizaton_url)


@app.route("/gr-oauth-authorized")
def confirm_oauth():
    """ Processes response for Goodreads OAuth """
    authorized = request.args.get("authorize")
    user = User.query.get(session.get("user_id"))

    if user:
        if authorized == "1":
            gr_sess = goodreads.get_auth_session(request_token, request_token_secret)
            user.goodreads_access_token = gr_sess.access_token
            user.goodreads_access_token_secret = gr_sess.access_token_secret
            user.is_goodreads_authorized = True
            db.session.commit()
            flash("Successfully authorized!", "success")

        else:
            flash("Authorization denied. Please try again.", "warning")

        return redirect("/user/{}".format(user.user_id))

    else:
        flash("Must be logged in to access this feature.", "danger")
        return redirect("/")


@app.route("/update-profile", methods=["POST"])
def update_profile():
    user_id = session.get("user_id")
    description = request.form.get("description")
    fav_book = request.form.get("fav-book")
    des_pub = request.form.get("descr-publ")
    fav_series_pub = request.form.get("fs-publ")
    fav_author_pub = request.form.get("fa-publ")

    user = User.query.get(user_id)

    if fav_book:
        user.fav_book = fav_book

    if description:
        user.description = description

    if des_pub:
        user.is_description_public = bool(int(des_pub))

    if fav_author_pub:
        user.is_fav_author_public = bool(int(fav_author_pub))

    if fav_series_pub:
        user.is_fav_series_public = bool(int(fav_series_pub))

    db.session.commit()

    flash("Info successfully updated!", "success")
    return redirect("/user/{}".format(user_id))


@app.route("/update-authors", methods=["POST"])
def update_authors():
    user_id = session.get("user_id")
    unfav_authors = request.form.getlist("author-remove")
    new_authors = request.form.get("new-author").strip().splitlines()
    # might change how I flash messages

    if unfav_authors:
        for author_id in unfav_authors:
            author = Fav_Author.query.filter_by(author_id=author_id, user_id=user_id).first()
            if author:
                db.session.delete(author)
                flash("Successfully removed {}".format(author.author.author_name), "success")

    if new_authors:
        for author_name in new_authors:
            author = Author.query.filter_by(author_name=author_name).first()

            if author:  # if author in database
                if Fav_Author.query.filter_by(author_id=author.author_id, user_id=user_id).first():
                    flash("You already liked {}!".format(author.author_name), "warning")

                else:
                    db.session.add(Fav_Author(author_id=author.author_id, user_id=user_id))
                    flash("Successfully added {}".format(author_name), "success")
            else:  # if author is NOT in database
                # unpack data?
                goodreads_info = get_author_goodreads_info(author_name)

                if author_name != goodreads_info[1]:  # name entered and name returned from goodreads do not match (indicates typo)
                    flash("Could not find {}. Did you mean {}?".format(author_name, goodreads_info[1]), "info")

                else:  # author is definitely NOT in database
                    # need to handle what should happen if it's None
                    db.session.add(Author(author_name=goodreads_info[1], goodreads_id=goodreads_info[0]))
                    db.session.commit()

                    author_id = Author.query.filter_by(author_name=author_name).first().author_id
                    db.session.add(Fav_Author(author_id=author_id, user_id=user_id))
                    flash("Successfully added {}".format(author_name), "success")

    db.session.commit()
    return redirect("/user/{}".format(user_id))


@app.route("/update-fav-author.json", methods=["POST"])
def update_fav_author():
    user_id = session.get("user_id")
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


@app.route("/get-author-id.json", methods=["POST"])
def get_author_id():
    a_name = request.form.get("author")
    author = Author.query.filter_by(author_name=a_name).first()

    if author:  # if the author is in the database
        return jsonify({"auth_status": "ok", "id": author.author_id})

    else:  # author is not in database under spelling provided
        goodreads_id, goodreads_name = get_author_goodreads_info(a_name)

        if goodreads_id:  # if this author is in goodreads
            author2 = Author.query.filter_by(goodreads_id=goodreads_id).first()

            if author2:  # if the author is already in the database, but under a different spelling
                return jsonify({"auth_status": "ok", "id": author2.author_id})

            else:  # if author is not in database
                db.session.add(Author(author_name=goodreads_name, goodreads_id=goodreads_id))
                db.session.commit()
                new_auth = Author.query.filter_by(goodreads_id=goodreads_id)
                return jsonify({"auth_status": "ok", "id": new_auth.author_id})

        else:  # author is not in goodreads
            pass


@app.route("/update-series", methods=["POST"])
def update_series():
    user_id = session.get("user_id")
    unfav_series = request.form.getlist("series-remove")
    new_series = request.form.getlist("series-add")
    # might change how I decide to flash messages

    if unfav_series:
        for series_id in unfav_series:
            series = Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first()
            if series:  # check to see if in database... useful just-in-case check, but not really needed
                db.session.delete(series)
                flash("Successfully removed {}".format(series.series.series_name), "success")

    if new_series:
        for series_id in new_series:
            series = Series.query.get(series_id)
            if Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first():
                flash("You already liked {}!".format(series.series_name), "warning")

            else:
                db.session.add(Fav_Series(series_id=series_id, user_id=user_id))
                flash("Successfully added {}".format(series.series_name), "success")

    # maybe figure out I want to handle if the series check fails later...

    db.session.commit()
    return redirect("/user/{}".format(user_id))


@app.route("/update-fav-series.json", methods=["POST"])
def update_fav_series():
    user_id = session.get("user_id")
    series_id = request.form.get("series_id")

    if user_id and series_id:
        if Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first():
            return jsonify({"result": "You have already favorited this series!"})

        else:
            db.session.add(Fav_Series(series_id=series_id, user_id=user_id))
            db.session.commit()
            return jsonify({"result": "New favorite series added!"})
    else:
        return jsonify({"result": "Something went wrong."})


@app.route("/author/<author_id>")
def show_author_info(author_id):
    """ Renders author info page """
    author = Author.query.get(author_id)

    if author:
        series = None

        if author.author_img:
            author_info = wikipedia.summary(author.author_name)
            author_info.replace("\n", " ")
            author_img = author.author_img

        else:

            author_pg = wikipedia.page(author.author_name)
            # handle any exceptions up here.
            author_img = None

            for link in author_pg.images:
                if author.author_name.split(" ")[-1] in link and link.endswith("jpg"):
                    author_img = link

            if author_img:
                author.author_img = author_img
                db.session.commit()

            author_info = author_pg.summary
            author_info.replace("\n", " ")

        if author.goodreads_id is None:
            possible_id = get_author_goodreads_info(author.author_name)[0]
            if possible_id:
                author.goodreads_id = possible_id
                db.session.commit()

        if author.goodreads_id:
            series = get_series_list_by_author(author.goodreads_id)

        return render_template("author_info.html", author=author, info=author_info, url=author_img, series=series)

    else:
        flash("Author does not exist. Please try again!", "danger")
        if "user_id" in session:
            return redirect("/user/{}".format(session["user_id"]))

        else:
            return redirect("/")


@app.route("/goodreads-follow-author/<author_id>")
def follow_goodreads_author(author_id):
    user = User.query.get(session.get("user_id"))
    author = Author.query.get(author_id)  # check to see if author exists as well
    if user:
        if user.is_goodreads_authorized:
            gr_sess = OAuth1Session(consumer_key=goodreads_key,
                                    consumer_secret=os.environ["GOODREADS_API_SECRET"],
                                    access_token=user.goodreads_access_token,
                                    access_token_secret=user.goodreads_access_token_secret)

            data = {'id': author.goodreads_id}  # check to see if goodreads id is present
            gr_sess.post('https://www.goodreads.com/author_followings', data)
            flash("Successfully followed {}".format(author.author_name), "success")
            return redirect("/author/{}".format(author.author_id))

        else:  # could redirect a person to allow them... modify the oauth-authorized route?
            flash("Not authorized to do this function.", "danger")
            return redirect("/")

    else:
        flash("Must be logged in to access this function.", "danger")
        return redirect("/")


@app.route("/series/<series_id>")
def show_series_info(series_id):
    """ Renders series info page """
    series = Series.query.get(series_id)

    if series:
        series_info = {}
        payload = {"key": goodreads_key, "id": series.goodreads_id}
        response = requests.get("https://www.goodreads.com/series/show/", params=payload)

        if response.status_code == 200:
            tree = ET.fromstring(response.content)
            s_info = tree.find("series")

            series_info["description"] = strip_tags(s_info.find("description").text.strip())
            series_info["length"] = s_info.find("primary_work_count").text
            series_works = list(s_info.find("series_works"))
            series_info["works"] = []

            for work in series_works:
                valid_positions = [str(i) for i in range(1, int(series_info["length"]) + 1)]
                # maybe make this a set?

                if work.find("user_position").text in valid_positions:
                    work_info = get_info_for_work(work)
                    title = work_info["title"]
                    pub_date = work_info["published"]
                    cover = work_info["cover"]

                    if pub_date is None:
                        if 'untitled' in title.lower():  # if the book currently has no title
                            pub_date = "TBA"

                        else:
                            pub_date = get_pub_date_with_title(title)

                    author = work_info["author"]
                    series_info["works"].append((title, author, pub_date, cover))
                    # might consider adding some sort of sorting to make sure books show up in order
                    # then again, they are in order on Goodreads so... idk

            if (len(series_info["works"]) != int(series_info["length"])):
                series_info["length"] = str(len(series_info["works"]))

        return render_template("series_info.html", series=series, info=series_info)

    else:
        flash("Series does not exist. Please try again!", "danger")

        if "user_id" in session:
            return redirect("/user/{}".format(session["user_id"]))

        else:
            return redirect("/")

if __name__ == "__main__":
    app.debug = True
    app.jinja_env.auto_reload = app.debug
    connect_to_db(app)
    DebugToolbarExtension(app)
    app.run(host="0.0.0.0")
