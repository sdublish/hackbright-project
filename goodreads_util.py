import os
import requests
import xml.etree.ElementTree as ET

from server_util import convert_string_to_datetime
from google_util import get_pub_date_with_title

goodreads_key = os.environ["GOODREADS_API_KEY"]


def get_author_goodreads_info(author_name):
    """ Given author name, returns (goodreads_id, goodreads_name), if it exists.
    Otherwise returns (None, None)."""
    goodreads_id = None
    goodreads_name = None

    payload = {"key": goodreads_key}
    url = "https://www.goodreads.com/api/author_url/{}".format(author_name)
    response = requests.get(url, params=payload)

    if response.status_code == 200:
        tree = ET.fromstring(response.content)

        if tree.find("author"):
            goodreads_id = tree.find("author").attrib["id"]
            goodreads_name = tree.find("author").find("name").text

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
        return list(by_user_position.values())[0]

    else:
        smallest_user_position = min(key for key in by_user_position if key is not None and key >= "1")
        return by_user_position[smallest_user_position]


def get_series_list_by_author(author_id):
    """ Queries the Goodreads API and gets a dictionary of series associated with this author id.
    If error occured, returns None. If no series are found, returns empty dictionary. """
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


def get_last_book_of_series(series_name, series_id, date, timeframe):
    """ Given a series name, date of search, and timeframe, returns a dictionary containing the info of the
    last book published in that series in the timeframe provided. If API error, returns
    a dictionary with key 'status' and value 'error'."""
    payload = {"key": goodreads_key, "id": series_id}
    response = requests.get("https://www.goodreads.com/series/show/", params=payload)

    if response.status_code == 200:
        tree = ET.fromstring(response.content)
        series_length = tree.find("series").find("primary_work_count").text
        series_works = list(tree.find("series").find("series_works"))
        by_user_position = {}

        for work in series_works:
            user_position = work.find("user_position").text
            by_user_position[user_position] = work

        title = 'untitled'
        published = None

        while ('untitled' in title.lower() and published is None) and series_length >= "1":
            work = by_user_position.get(series_length)

            if work is None:
                last_position = max(by_user_position.keys())
                work = by_user_position[last_position]

            work_info = get_info_for_work(work)
            title = work_info["title"]
            published = work_info["published"]
            cover = work_info["cover"]

            series_length = str(int(series_length) - 1)

        if published is None:
            published = get_pub_date_with_title(title)

        if published == "error":
            return {"status": "error"}

        result = (title, published, cover)

        pdate = convert_string_to_datetime(published)

        if timeframe and not (date <= pdate <= date + timeframe):
            if pdate < date:
                result = (None, None, "http://sendmeglobal.net/images/404.png")

            else:
                while series_length >= "1":
                    work = by_user_position[series_length]
                    work_info = get_info_for_work(work)
                    title2 = work_info["title"]
                    published2 = work_info["published"]
                    cover = work_info["cover"]

                    if published2 is None:
                        published2 = get_pub_date_with_title(title)

                    pdate2 = convert_string_to_datetime(published2)

                    if pdate2 < date:
                        result = (None, None, "http://sendmeglobal.net/images/404.png")
                        break

                    elif pdate <= pdate2 <= date + timeframe:
                        result = (title2, pdate2, cover)
                        break

                    series_length = str(int(series_length) - 1)

            if series_length == "0":
                result = (None, None, "http://sendmeglobal.net/images/404.png")

        return {'status': 'ok', 'results': result}

    else:
        return {'status': 'error'}


def get_info_for_work(work):
    """ Given a work, gets the title, author, cover image, and publication date for said book"""
    title = work.find("work").find("best_book").find("title").text
    author = work.find("work").find("best_book").find("author").find("name").text
    image = work.find("work").find("best_book").find("image_url").text.strip()
    pub = None

    p_year = work.find("work").find("original_publication_year").text
    p_month = work.find("work").find("original_publication_month").text
    p_date = work.find("work").find("original_publication_day").text

    if p_year and p_month and p_date:
        pub = "{}-{}-{}".format(p_year, p_month.zfill(2), p_date.zfill(2))

    elif p_year and p_month:
        pub = "{}-{}".format(p_year, p_month.zfill(2))

    elif p_year:
        pub = p_year

    return {'title': title, 'published': pub, "author": author, "cover": image}
