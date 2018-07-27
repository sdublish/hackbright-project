""" Models for project """

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    """ Users of project """
    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    fname = db.Column(db.String(30), nullable=False)
    lname = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=True)  # remove
    zipcode = db.Column(db.String(6), nullable=True)  # remove
    fav_book = db.Column(db.String(60), nullable=True)
    # add description column (db.Text or something like that)
    # add is_fav_series_private
    # add is_fav_author_private
    # storing goodreads authorization key??

    fav_authors = db.relationship("Fav_Author")
    fav_series = db.relationship("Fav_Series")

    def __repr__(self):
        return "<User {}, name:{} {}, email:{}>".format(self.user_id, self.fname, self.lname, self.email)


class Author(db.Model):
    """ Authors included in project """
    __tablename__ = "authors"

    author_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    author_name = db.Column(db.String(100), nullable=False)
    goodreads_id = db.Column(db.String(15), nullable=True)

    favorited_by = db.relationship("Fav_Author")

    def __repr__(self):
        return "<Author {}, Name: {}>".format(self.author_id, self.author_name)


class Fav_Author(db.Model):
    """ Association table to keep track of favorite authors"""

    __tablename__ = "fav_authors"

    fav_author_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.author_id"), nullable=False)

    user = db.relationship("User")
    author = db.relationship("Author")

    def __repr__(self):
        return "<Fav Author {}, Author {} favorited by User {}>".format(self.fav_author_id, self.author_id, self.user_id)


class Series(db.Model):
    """ Series included in project """
    __tablename__ = "series"

    series_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    series_name = db.Column(db.String(200), nullable=False)
    goodreads_id = db.Column(db.String(50), nullable=False)

    favorited_by = db.relationship("Fav_Series")

    def __repr__(self):
        return "<Series {}, series name {}>".format(self.series_id, self.series_name)


class Fav_Series(db.Model):
    """ Association table to keep track of favorited series"""
    __tablename__ = "fav_series"

    fav_series_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    series_id = db.Column(db.Integer, db.ForeignKey("series.series_id"), nullable=False)

    series = db.relationship("Series")
    user = db.relationship("User")

    def __repr__(self):
        return "<Fav Series {}, series {} favorited by User {}>".format(self.fav_series_id, self.series_id, self.user_id)


def example_data():
    """ Data used for tests.py"""
    # in case this is run twice, empty out existing data
    Fav_Series.query.delete()
    Fav_Author.query.delete()
    User.query.delete()
    Author.query.delete()
    Series.query.delete()

    u1 = User(fname="Bob", lname="Bob", email="bob@bob.com", password=generate_password_hash("bob"), fav_book="Bob's First Adventure")
    u2 = User(fname="Jane", lname="Debugger", email="jdeb@gmail.com", password=generate_password_hash("bugs"))
    a1 = Author(author_name="Bob Bob", goodreads_id="8388")
    a2 = Author(author_name="The Cool Dude")
    s1 = Series(series_name="Bob's Adventure", goodreads_id="2034")
    db.session.add_all([u1, u2, a1, a2, s1])
    db.session.commit()

    fs1 = Fav_Series(user_id=1, series_id=1)
    fa1 = Fav_Author(user_id=1, author_id=1)
    fa2 = Fav_Author(user_id=2, author_id=2)
    db.session.add_all([fs1, fa1, fa2])
    db.session.commit()

######### HELPER FUNCTIONS ###################################################################


def connect_to_db(app, url="postgresql:///project"):
    """ Connects to database"""
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db. init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print("Connected to DB.")
