""" Data to seed database for testing"""

from model import User, Author, Fav_Author, Series, Fav_Series
from model import connect_to_db, db
from server import app


def load_users():
    print("Loading users")
    """ Loads test users into database"""

    # delete all rows so we don't add duplicate info
    User.query.delete()

    db.session.add(User(fname="Bob", lname="Bob", email="bob@bob.com", password="bob"))
    db.session.add(User(fname="Jane", lname="Debug", email="jdebug@gmail.com", password="bugs"))
    db.session.add(User(fname="Sam", lname="Dragon", email="sdragon@hotmail.com", password="dragons"))
    db.session.add(User(fname="Tessa", lname="Test", email="tester@test.com", password="test"))

    db.session.commit()


def load_authors():
    print("Loading authors")
    """Loads sample authors into database"""

    # delete all rows so we don't add duplicate info
    Author.query.delete()

    db.session.add(Author(author_name="Brandon Sanderson", goodreads_id="38550"))
    db.session.add(Author(author_name="William Shakespeare", goodreads_id="947"))
    db.session.add(Author(author_name="Lois Lowry", goodreads_id="2493"))
    db.session.add(Author(author_name="Dr.Seuss", goodreads_id="61105"))
    db.session.add(Author(author_name="Stephen King"))

    db.session.commit()


def load_fav_authors():
    """Loads sample users' favorite authors into database"""
    print("Loading favorite authors")

    # delete all rows so we don't add duplicate info
    Fav_Author.query.delete()

    db.session.add(Fav_Author(user_id=1, author_id=4))
    db.session.add(Fav_Author(user_id=2, author_id=3))
    db.session.add(Fav_Author(user_id=2, author_id=1))
    db.session.add(Fav_Author(user_id=4, author_id=2))

    db.session.commit()


def load_series():
    """Loads sample series into database"""
    print("Loading series")

    # delete all rows so we don't add duplicate info
    Series.query.delete()

    db.session.add(Series(series_name="Mistborn", goodreads_id="40910"))
    db.session.add(Series(series_name="Harry Potter", goodreads_id="45175"))
    db.session.add(Series(series_name="The Giver", goodreads_id="43606"))

    db.session.commit()


def load_fav_series():
    """ Loads sample favorite series into database"""
    print("Loading favorite series")

    # delete all rows so we don't add duplicate info
    Fav_Series.query.delete()

    db.session.add(Fav_Series(user_id=2, series_id=1))
    db.session.add(Fav_Series(user_id=3, series_id=3))
    db.session.add(Fav_Series(user_id=3, series_id=2))
    db.session.add(Fav_Series(user_id=2, series_id=2))

    db.session.commit()


if __name__ == "__main__":
    connect_to_db(app)
    db.create_all()

    load_users()
    load_authors()
    load_series()
    load_fav_authors()
    load_fav_series()
