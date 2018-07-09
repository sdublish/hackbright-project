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
    # any other fields go here

    fav_authors = db.relationship("Fav_Author")

    def __repr__(self):
        return "<User {}, name:{} {}, email:{}>".format(self.user_id, self.fname, self.lname, self.email)


class Author(db.Model):
    """ Authors included in project """
    __tablename__ = "authors"

    author_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    author_name = db.Column(db.String(100), nullable=False)
    google_book_id = db.Column(db.String(100), nullable=True)
    goodreads_id = db.Column(db.Integer, nullable=True)

    favorited_by = db.relationship("Fav_Author")  # not sure if useful

    def __repr__(self):
        return "<Author {}, Name: {}>".format(self.author_id, self.author_name)


class Fav_Author(db.Model):
    """ Association table to connect users to favorite authors"""

    __tablename__ = "fav_authors"

    fav_author_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    author_id = db.Column(db.Integer, db.ForeignKey("authors.author_id"))

    user = db.relationship("User")
    author = db.relationship("Author")

    def __repr__(self):
        return "<Fav Author {}, Author {} favorited by {}>".format(self.fav_author_id, self.author_id, self.user_id)

######### HELPER FUNCTION ###################################################################


def connect_to_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///project"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db. init_app(app)