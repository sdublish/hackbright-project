""" Models for project """

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """ Users of project """
    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    fname = db.Column(db.String(30), nullable=False)
    lname = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    zipcode = db.Column(db.String(6), nullable=True)
    fav_book = db.Column(db.String(60), nullable=True)

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
    goodreads_id = db.Column(db.String(50), nullable=True)

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


######### HELPER FUNCTION ###################################################################


def connect_to_db(app):
    """ Connects to database"""
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///project"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db. init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print("Connected to DB.")
