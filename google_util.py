import requests
import os

google_books_key = os.environ["GOOGLE_BOOKS_API_KEY"]


def get_pub_date_with_title(title):
    """ Gets the publication date for a book based off its title"""
    payload = {"q": title,
               "langRestrict": "en",
               "printType": "books",
               "key": google_books_key
               }
    # might consider some more checks to make sure search is going okay

    r2 = requests.get("https://www.googleapis.com/books/v1/volumes", params=payload)
    r2_json = r2.json()
    google_id = r2_json["items"][0]["id"]
    return get_pub_date_with_book_id(google_id)


def get_pub_date_with_book_id(google_id):
    """ Gets a publicatioon date for a book based off its Google Book ID"""
    payload = {"key": google_books_key}
    url = "https://www.googleapis.com/books/v1/volumes/{}".format(google_id)

    r2 = requests.get(url, params=payload)
    # can do another check here to see if request went okay
    results_2 = r2.json()
    return results_2["volumeInfo"]["publishedDate"]
