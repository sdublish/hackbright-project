from html.parser import HTMLParser
from datetime import datetime


class MLStripper(HTMLParser):
    """ Class to strip plaintext of any html tags"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    """ Function that strips tags based off MLStripper class """
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def convert_string_to_datetime(date_string):
    """ Given a string representing the date, returns a datetime
    object corresponding to said string."""
    date_split = date_string.split("-")

     # might make sense to change the order of these if statements around
    if len(date_split) == 1:
        return datetime.strptime(date_string, "%Y")
    elif len(date_split) == 2:
        return datetime.strptime(date_string, "%Y-%m")
    else:
        return datetime.strptime(date_string, "%Y-%m-%d")