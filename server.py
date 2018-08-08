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

# code for debugging purposes
from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined


app = Flask(__name__)
# below is for debugging purposes
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
timeframes = {183: "First Book to be Published in Next Six Months", 365: "First Book to be Published in Next Year",
              730: "First Book to be Published in In Two Years", 0: "Most Recently Published Book"}

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
    """ Returns search results based off author or series inputted"""
    author = request.form.get("author")
    series_id = request.form.get("series")
    timeframe = int(request.form.get("timeframe"))
    tf_str = timeframes[timeframe]

    date = request.form.get("date")
    date_str = " ".join(date.split()[1:])
    py_date = datetime.strptime(date_str, "%b %d %Y")
    td = timedelta(days=timeframe)

    if author:
        payload = {"q": "inauthor:" + author,
                   "langRestrict": "en",
                   "orderBy": "newest",
                   "printType": "books",
                   "key": google_books_key
                   }

        response = requests.get("https://www.googleapis.com/books/v1/volumes", params=payload)

        if response.status_code == 200:
            results = response.json()
            next_book = results["items"][0]["volumeInfo"]
            next_book_cover = no_cover_img

            if results["items"][0]["volumeInfo"].get("imageLinks"):
                next_book_cover = results["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]

            next_book_id = results["items"][0]["id"]

            published_date = get_pub_date_with_book_id(next_book_id)

            if published_date == "error":
                return jsonify({"status": "error"})

            pdate = convert_string_to_datetime(published_date)

            result = ("Title: <i>{}</i>".format(next_book["title"]), "Publication date: {}".format(published_date), next_book_cover)

            if (not td) and not (pdate <= py_date):
                for work in results["items"][1:]:
                    date2 = get_pub_date_with_book_id(work["id"])
                    pdate2 = convert_string_to_datetime(date2)
                    next_book_cover2 = no_cover_img

                    if work["volumeInfo"].get("imageLinks"):
                        next_book_cover2 = work["volumeInfo"]["imageLinks"]["thumbnail"]

                    if (pdate2 <= py_date):
                        result = ("Title: <i>{}</i>".format(work["volumeInfo"]["title"]), "Publication date: {}".format(date2), next_book_cover2)
                        break

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
                            result = ("Title: <i>{}</i>".format(work["volumeInfo"]["title"]), "Publication date: {}".format(date2), next_book_cover2)
                            break

            if "search_history" in session:
                search = (date, tf_str, author, result)
                # this looks redundant, but if I try to modify the session value directly
                # it doesn't update, so it has to be like this
                s_history = session["search_history"]
                s_history.append(search)
                session["search_history"] = s_history

            return jsonify({"status": "ok", "results": result})

        return jsonify({"status": "error"})

    else:  # if series is being searched
        series = Series.query.get(series_id)
        results = get_last_book_of_series(series.series_name, series.goodreads_id, py_date, td)

        if "search_history" in session:
            search = (date, tf_str, series.series_name, results["results"])
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
        return jsonify({"status": "Email sent! Look for {} in your inbox.".format(os.environ["APP_EMAIL"])})

    else:
        return jsonify({"status": "An error occurred. Make sure you're signed in."})


@app.route("/adv-search")
def show_adv_search():
    """ Renders advanced search page """
    return render_template("adv-search.html")


@app.route("/by-author", methods=["POST"])
def search_by_author():
    """ Returns list of series associated with author"""
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
        possible_id, possible_name = get_author_goodreads_info(author_name)

        if possible_id:
            possible_author = Author.query.filter_by(goodreads_id=possible_id).first()

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
                db.session.add(Author(author_name=possible_name, goodreads_id=possible_id))
                db.session.commit()
                series_info = get_series_list_by_author(possible_id)

                if series_info is not None:  # if we get results
                    if author_name != possible_name:
                        flash("Showing results for {} instead of {}".format(possible_name, author_name), "info")

                    title = "Series by {}".format(possible_name)
                    return render_template("series_results.html", series=series_info, title=title, tfs=timeframes)

                else:  # did not get results/returned None
                    flash("An error occured. Please try again", "danger")
                    return redirect("/adv-search")

        else:  # if no author id is returned
            flash("Could not find an author with that name. Please try again.", "warning")
            return redirect("/adv-search")


@app.route("/by-book", methods=["POST"])
def search_by_book():
    """ Returns search results based off book title"""
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
    """ Shows series linked to book """
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
    """ Returns last book of series """
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
            search = (date, tf_str, series_name, results["results"])
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
    """ Logs in user if information matches what is in database """
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
        flash("You are now logged out of Bibliofind!", "success")

    else:  # safety check just in case someome tries to access manually
        flash("You can't log out if you're not logged in!", "warning")

    return redirect("/")


@app.route("/sign-up", methods=["GET"])
def show_signup():
    """ Renders sign-up page """
    return render_template("signup.html")


@app.route("/sign-up", methods=["POST"])
def signup():
    """ Signs up user if information is entered correctly """
    email = request.form.get("email")

    if User.query.filter_by(email=email).first():  # if email exists in database
        flash("Email already exists. Please try again.", "warning")
        return redirect("/sign-up")

    else:
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        password = request.form.get("password")

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
    """ Updates user profile based off what was inputted """
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
    """ Updates who is the user's favorites authors """
    user_id = session.get("user_id")
    unfav_authors = request.form.getlist("author-remove")
    new_authors = request.form.get("new-author").strip().splitlines()
    # might change how I flash messages

    if unfav_authors:
        auth_names = "Successfully removed:"
        for author_id in unfav_authors:
            author = Fav_Author.query.filter_by(author_id=author_id, user_id=user_id).first()

            if author:
                db.session.delete(author)
                auth_names += " {},".format(author.author.author_name)

        flash(auth_names.rstrip(","), "success")

    if new_authors:
        auth_fav = ""
        auth_add = ""

        for author_name in new_authors:
            author = Author.query.filter_by(author_name=author_name).first()

            if author:  # if author in database
                if Fav_Author.query.filter_by(author_id=author.author_id, user_id=user_id).first():
                    auth_fav += " {},".format(author.author_name)

                else:
                    db.session.add(Fav_Author(author_id=author.author_id, user_id=user_id))
                    auth_add += " {},".format(author_name)

            else:  # if author is NOT in database
                gr_id, gr_name = get_author_goodreads_info(author_name)

                if gr_id:

                    if author_name != gr_name:  # name entered and name returned from goodreads do not match (indicates typo)
                        flash("Could not find {}. Did you mean {}?".format(author_name, gr_name), "info")

                    else:  # author is definitely NOT in database
                        db.session.add(Author(author_name=gr_name, goodreads_id=gr_id))
                        db.session.commit()

                        author_id = Author.query.filter_by(author_name=author_name).first().author_id
                        db.session.add(Fav_Author(author_id=author_id, user_id=user_id))
                        auth_add += " {},".format(author_name)

                else:  # author is not in Goodreaeds
                        flash("{}} is not in Goodreads, so cannot add to favorites. Sorry!".format(author_name), "warning")

        if auth_fav:
            flash("You already liked:{}".format(auth_fav.rstrip(",")), "warning")

        if auth_add:
            flash("Successfully added:{}".format(auth_add.rstrip(",")), "success")

    db.session.commit()
    return redirect("/user/{}".format(user_id))


@app.route("/update-fav-author.json", methods=["POST"])
def update_fav_author():
    """ Adds author to user's list of favorite authors """
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
    """ Returns author id for author name inputted """
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
                new_auth = Author.query.filter_by(goodreads_id=goodreads_id).first()
                return jsonify({"auth_status": "ok", "id": new_auth.author_id})

        else:  # author is not in goodreads
            return jsonify({"auth_status": "error"})


@app.route("/update-series", methods=["POST"])
def update_series():
    """ Updates list of favorite series for user """
    user_id = session.get("user_id")
    unfav_series = request.form.getlist("series-remove")
    new_series = request.form.getlist("series-add")

    if unfav_series:
        series_unfav = "Successfully removed:"

        for series_id in unfav_series:
            series = Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first()
            if series:  # check to see if in database... useful just-in-case check, but not really needed
                db.session.delete(series)
                series_unfav += " {},".format(series.series.series_name)

        flash(series_unfav.rstrip(","), "success")

    if new_series:
        series_fav = ""
        series_add = ""

        for series_id in new_series:
            series = Series.query.get(series_id)

            if Fav_Series.query.filter_by(series_id=series_id, user_id=user_id).first():
                series_fav += " {},".format(series.series_name)

            else:
                db.session.add(Fav_Series(series_id=series_id, user_id=user_id))
                series_add += " {},".format(series.series_name)

        if series_fav:
            flash("You already liked:{}".format(series_fav.rstrip(",")), "warning")

        if series_add:
            flash("Successfullly added:{}".format(series_add.rstrip(",")), "success")

    db.session.commit()
    return redirect("/user/{}".format(user_id))


@app.route("/get-series-id.json", methods=["POST"])
def get_series_id():
    """ Returns series id based off series name """
    series_name = request.form.get("series_name")
    series = Series.query.filter_by(series_name=series_name)

    if series:
        return jsonify({"status": "ok", "id": series.series_id})
    else:
        return jsonify({"status": "Could not find series. Please try again."})


@app.route("/update-fav-series.json", methods=["POST"])
def update_fav_series():
    """ Adds series to user's favorite series """
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
    """ Follows author on Goodreads linked to user's account """
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
                valid_positions = set(str(i) for i in range(1, int(series_info["length"]) + 1))

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
    app.debug = False
    # if debugging, uncomment line below
    # app.debug = True
    app.jinja_env.auto_reload = app.debug
    connect_to_db(app)
    # line below is for debugging purposes
    # DebugToolbarExtension(app)
    app.run(host="0.0.0.0")
