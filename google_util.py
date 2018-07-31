import requests
import os

google_books_key = os.environ["GOOGLE_BOOKS_API_KEY"]


def get_pub_date_with_title(title):
    """ Gets the publication date for a book based off its title. Returns string
    with value error if there is an API error. """
    payload = {"q": title,
               "langRestrict": "en",
               "printType": "books",
               "key": google_books_key
               }

    r2 = requests.get("https://www.googleapis.com/books/v1/volumes", params=payload)

    if r2.status_code == 200:
        r2_json = r2.json()
        google_id = r2_json["items"][0]["id"]
        return get_pub_date_with_book_id(google_id)

    else:
        return "error"


def get_pub_date_with_book_id(google_id):
    """ Gets a publicatioon date for a book based off its Google Book ID. Returns
    string with value error if there is an API error."""
    payload = {"key": google_books_key}
    url = "https://www.googleapis.com/books/v1/volumes/{}".format(google_id)
    r2 = requests.get(url, params=payload)

    if r2.status_code == 200:
        results_2 = r2.json()
        return results_2["volumeInfo"]["publishedDate"]

    else:
        return "error"
