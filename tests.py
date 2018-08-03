""" Tests for project """

from unittest import TestCase, main
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from unittest.mock import patch
from flask import session

from server import app
from model import connect_to_db, db, example_data
from goodreads_util import (sort_series, get_info_for_work, get_author_goodreads_info,
                            get_series_list_by_author, get_last_book_of_series)
from google_util import get_pub_date_with_book_id, get_pub_date_with_title
from server_util import convert_string_to_datetime, strip_tags


class ServerUtilTests(TestCase):
    """ Testing server utility functions """
    def test_convert_datetime_year(self):
        """ Makes sure function turns a string with year-only into a datetime object"""
        self.assertEqual(convert_string_to_datetime("2016"), datetime(year=2016, month=1, day=1))

    def test_convert_datetime_year_mon(self):
        """ Tests to see if function converts string of format year-month properly"""
        self.assertEqual(convert_string_to_datetime("2016-02"), datetime(year=2016, month=2, day=1))

    def test_convert_datetime_year_mon_day(self):
        """Tests to see if function converts string of format year-month-day properly"""
        self.assertEqual(convert_string_to_datetime("2016-02-02"), datetime(year=2016, month=2, day=2))

    def test_strip_tags_html(self):
        """Tests strip_tags functionality when html is present"""
        test_str = "<b> Look at this <i>test</i> string! </b>"
        self.assertEqual(strip_tags(test_str).strip(), "Look at this test string!")

    def test_strip_tags_no_html(self):
        """Tests strip tags functionality when no html is present"""
        test_str = "BOO"
        self.assertEqual(strip_tags(test_str), test_str)


class GoogleUtilTests(TestCase):
    """Testing Google Books Utility Functions"""
    def test_pub_date_with_book_id(self):
        """Tests to see if function returns date when given a dictionary from API"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.json.return_value = {"volumeInfo": {"publishedDate": "2016-07-07"}}
            self.assertEqual("2016-07-07", get_pub_date_with_book_id("1"))

    def test_pub_date_with_book_id_error(self):
        """ Tests to see if function returns string error when API error occurs"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 400
            self.assertEqual("error", get_pub_date_with_book_id("1"))

    def test_pub_date_with_title(self):
        """ Tests to see if function returns date when given a title"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.json.return_value = {"items": [{"id": "1"}]}
            with patch("google_util.get_pub_date_with_book_id") as mock_result:
                mock_result.return_value = "2016-08-03"
                self.assertEqual("2016-08-03", get_pub_date_with_title("Title"))

    def test_pub_date_with_title_error(self):
        """Tests to see if function returns string error when API error occurs"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 400
            self.assertEqual("error", get_pub_date_with_title("Title"))


class GoodreadsUtilTests(TestCase):
    """ Tests for Goodreads Utility Functions"""
    def test_sort_series_zero_series(self):
        """ Tests to see if sort_series functions returns an empty dictionary if passed in an empty list"""
        self.assertEqual(sort_series([]), {})

    def test_sort_series_one_series(self):
        """ Tests to see if sort_series returns a dictionary when passed in one series"""
        test_lst = []
        test_xml = """<series_work>
        <user_position>1</user_position>
        <series>
            <id>400</id>
            <title>Test</title>
        </series>
        </series_work>"""
        test_lst.append(ET.fromstring(test_xml))
        self.assertEqual(sort_series(test_lst), {"400": "Test"})

    def test_sort_series_two_series(self):
        """Tests to see if sort_series returns a dictionary with the right id when passed in two series of different user_position values"""
        test_xml = """<series_works>
        <series_work> <user_position>1</user_position>
        <series>
        <id>5</id> <title>The Answer</title>
        </series>
        </series_work>
        <series_work><user_position>5</user_position>
        <series>
        <id>40</id> <title>Not The Answer</title>
        </series>
        </series_work>
        </series_works>
        """
        test_lst = list(ET.fromstring(test_xml))
        self.assertEqual(sort_series(test_lst), {"5": "The Answer"})

    def test_sort_series_multi_series(self):
        """Tests to see if sort_series returns correct results when given multiple series of different user_positions"""
        test_xml = """<series_works>
        <series_work> <user_position>1</user_position>
        <series>
        <id>5</id> <title>The Answer</title>
        </series>
        </series_work>
        <series_work><user_position>5</user_position>
        <series>
        <id>40</id> <title>Not The Answer</title>
        </series>
        </series_work>
        <series_work> <user_position>0.5</user_position>
        <series>
        <id>573</id><title>Not Right</title>
        </series>
        </series_work>
        <series_work> <user_position>1</user_position>
        <series>
        <id>60</id> <title>Another Answer</title>
        </series>
        </series_work>
        <series_work> <user_position>5</user_position>
        <series>
        <id>7</id> <title>Wrong!</title>
        </series>
        </series_work>
        </series_works>
        """

        test_lst = list(ET.fromstring(test_xml))
        self.assertEqual(sort_series(test_lst), {"5": "The Answer", "60": "Another Answer"})

    def test_get_info_for_work_none(self):
        """Tests to see if get_info_for_work works if no publication date is given"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>A Test?!</title>
        <author> <name>Bob Smith</name></author>
        <image_url> url </image_url>
        </best_book>
        <original_publication_year/>
        <original_publication_month/>
        <original_publication_day/>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "A Test?!", "published": None, "author": "Bob Smith", "cover": "url"})

    def test_get_info_for_work_year(self):
        """Tests to see if get_info_for_work returns info when given publication year"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>Test</title>
        <author> <name>Bob Bob</name></author>
        <image_url> url </image_url>
        </best_book>
        <original_publication_year>2016</original_publication_year>
        <original_publication_month/>
        <original_publication_day/>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "Test", "published": "2016", "author": "Bob Bob", "cover": "url"})

    def test_get_info_for_work_year_mon(self):
        """Tests to see if get_info_for_work gives results if work has publication month and year"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>Test 2</title>
        <author> <name>Smith Bob</name></author>
        <image_url> url </image_url>
        </best_book>
        <original_publication_year>2016</original_publication_year>
        <original_publication_month>3</original_publication_month>
        <original_publication_day/>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "Test 2", "published": "2016-03", "author": "Smith Bob", "cover": "url"})

    def test_get_info_for_work_year_mon_day(self):
        """Tests to see if get_info_for_work works if all publication info is given"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>George's Best Day</title>
        <author> <name>George Gold</name></author>
        <image_url>url</image_url>
        </best_book>
        <original_publication_year>2016</original_publication_year>
        <original_publication_month>4</original_publication_month>
        <original_publication_day>9</original_publication_day>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "George's Best Day", "published": "2016-04-09", "author": "George Gold", "cover": "url"})

    def test_author_goodreads_info_error(self):
        """ Checks to see if function returns (None, None) when status code is not 200"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 400
            self.assertEqual((None, None), get_author_goodreads_info("Doesn't Exist"))

    def test_author_goodreads_info_no_info(self):
        """Tests to see if function returns (None, None) if no author information is provided"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<Goodreads></Goodreads>"
            self.assertEqual((None, None), get_author_goodreads_info("John Doe"))

    def test_author_goodreads_info_exists(self):
        """ Checks to see if function returns proper info when status code is 200"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<Goodreads><author id='40'><name>John Doe</name></author></Goodreads>"
            self.assertEqual(("40", "John Doe"), get_author_goodreads_info("John Doe"))

    def test_get_series_list_by_author_error(self):
        """ Tests to see if function returns None when an error occured"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 400
            self.assertIsNone(get_series_list_by_author(1))

    def test_get_series_list_by_author_no_series(self):
        """Tests to see if function returns an empty dictionary if no series are present"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<series> </series>"
            self.assertEqual({}, get_series_list_by_author(1))

    def test_get_series_list_by_author_with_series(self):
        """ Tests to see if get_series_list_by_author returns series when they are present"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<response><series_works><book></book></series_works></response>"
            with patch("goodreads_util.sort_series") as mock_sort:
                mock_sort.return_value = {"1": "a series"}
                self.assertEqual(get_series_list_by_author("1"), {"1": "a series"})

    def test_get_last_books_of_series_error(self):
        """ Tests to see if function returns error if issue occurs during API call"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 400
            self.assertEqual({'status': 'error'}, get_last_book_of_series("a", "b", 1, 1))

    def test_get_last_book_of_series_default(self):
        """ Tests to see if function returns expected value when searching in default timeframe"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = """<response><series>
            <primary_work_count>2</primary_work_count>
            <series_works><series_work>
            <user_position> 2 </user_position>
            <work> <best_book> <title>Test 2</title>
            <author> <name>Smith Bob</name></author>
            <image_url> url </image_url></best_book>
            <original_publication_year>2016</original_publication_year>
            <original_publication_month>3</original_publication_month>
            <original_publication_day>9</original_publication_day>
            </work></series_work></series_works></series></response>"""
            exp_result = ('Test 2', '2016-03-09', 'url')
            exp_dict = {'status': 'ok', 'most_recent': exp_result, 'results': exp_result}
            self.assertEqual(exp_dict, get_last_book_of_series('series', '1', 'date', 0))

    def test_get_last_book_of_series_not_in_range(self):
        """Tests to see if function returns expected value when there are no books in search range"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = """<response><series>
            <primary_work_count>2</primary_work_count>
            <series_works><series_work>
            <user_position> 2 </user_position>
            <work> <best_book> <title>Test 2</title>
            <author> <name>Smith Bob</name></author>
            <image_url> url </image_url></best_book>
            <original_publication_year>2016</original_publication_year>
            <original_publication_month>3</original_publication_month>
            <original_publication_day>9</original_publication_day>
            </work></series_work></series_works></series></response>"""
            exp_mr = ('Test 2', '2016-03-09', 'url')
            exp_r = (None, None, "http://sendmeglobal.net/images/404.png")
            self.assertEqual({'status': 'ok', 'most_recent': exp_mr, "results": exp_r}, get_last_book_of_series('series', 1, datetime.now(), timedelta(days=183)))


class FlaskNotLoggedInTests(TestCase):
    """ Integration tests for when user is not logged in"""
    def setUp(self):
        """Sets up app for a not-logged in user"""
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_homepage(self):
        """ Tests to see if homepage renders properly"""
        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Welcome to Bibliofind", result.data)

    def test_login_page(self):
        """ Tests to see if login page renders properly"""
        result = self.client.get("/login")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Login", result.data)

    def test_logout(self):
        """Tests to see if user is redirected correctly if attempting to logout when not logged in"""
        result = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"You can&#39;t log out", result.data)
        self.assertIn(b"Bibliofind", result.data)

    def test_signup_page(self):
        """ Tests to see if signup page renders properly"""
        result = self.client.get("/sign-up")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Sign Up", result.data)

    def test_adv_search_page(self):
        """ Tests to see if advanced search page renders properly"""
        result = self.client.get("/adv-search")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Advanced Search", result.data)

    def test_book_search_error(self):
        """ Tests to see if, if API does not send a proper request, searching by book goes back to advanced search page"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 400
            result = self.client.post("/by-book", data={"title": "Failure"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Something went wrong", result.data)
        self.assertIn(b"Advanced Search", result.data)

    def test_book_search_no_books(self):
        """Tests to see if by-book renders properly if no books are provided from search"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<response> <search><results></results></search></response>"
            result = self.client.post("/by-book", data={"title": "Gibberish"})
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Search Results for Gibberish", result.data)
        self.assertIn(b"No books were found", result.data)

    def test_book_search_shows_results(self):
        """ Tests to see if by-book shows the series returned in API response """
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = """
            <Response> <search> <results>
            <work><id>300</id>
            <best_book>
            <title>An Answer</title>
            <author><name>Jane Doe</name></author>
            </best_book>
            </work>
            </results></search></Response>
            """
            result = self.client.post("/by-book", data={"title": "An Answer"})
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Search Results for An Answer", result.data)
        self.assertIn(b"An Answer by Jane Doe", result.data)

    def test_book_series_no_id(self):
        """ Tests to see if book-series redirects properly if no book_id is provided"""
        result = self.client.post("/book-series", data={"book": "|| Failure"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Something went wrong", result.data)
        self.assertIn(b"Advanced Search", result.data)

    def test_book_series_error(self):
        """Tests to see if book-series redirects properly if error occurs in API call"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 400
            result = self.client.post("/book-series", data={"book": "1|| Failure"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Something went wrong", result.data)
        self.assertIn(b"Advanced Search", result.data)

    def test_book_series_no_series(self):
        """ Tests to see if book-series shows all series related to book if API call is successful"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<response> </response>"
            result = self.client.post("/book-series", data={"book": "1|| Seriesless"})
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Series That Seriesless", result.data)
        self.assertIn(b"No series were found", result.data)

    def test_book_series_series(self):
        """ Tests to see if book-series show all series related to book if API call is successful and series are there"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<response><series_works><series_work></series_work></series_works></response>"
            with patch("server.sort_series") as mock_series:
                mock_series.return_value = {"1": "A series"}
                result = self.client.post("/book-series", data={"book": "1||Yay Series"})
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Series That Yay Series", result.data)
        self.assertIn(b"A series", result.data)


class FlaskNotLoggedInDatabaseTests(TestCase):
    """ Integration tests for when user is not logged in and have database interactions"""

    def setUp(self):
        """Sets up app for a not-logged in user"""
        self.client = app.test_client()
        app.config["TESTING"] = True

        connect_to_db(app, "postgresql:///testdb")

        db.create_all()
        example_data()

    def tearDown(self):
        """ Tear down to ensure database is the same for each test"""
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    def test_signup_user_exists(self):
        """ Tests to see if user is redirected properly if trying to sign up with email which is already in database"""
        result = self.client.post("/sign-up", data={"email": "bob@bob.com"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Email already exists", result.data)
        self.assertIn(b"Sign Up", result.data)

    def test_signup_error(self):
        """Tests to see if user is redirected properly if they do not sign up properly"""
        result = self.client.post("/sign-up", data={"email": "hello@world.com", "password": "yay"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Please input values", result.data)
        self.assertIn(b"Sign Up", result.data)

    def test_signup_success(self):
        """ Tests to see if user can sign up for an account"""
        with self.client as c:
            result = c.post("/sign-up", data={"email": "test@test.com",
                                              "fname": "Tessa", "lname": "Test",
                                              "password": "test"}, follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(session["user_id"], 3)
            self.assertEqual(session["search_history"], [])
            self.assertIn(b"New user", result.data)
            self.assertIn(b"You are now logged in", result.data)
            self.assertIn(b"Tessa Test", result.data)

    def test_user_login_success(self):
        """Tests to see if a user is redirected to the proper page if they enter the right login info"""
        with self.client as c:
            result = c.post("/login", data={"email": "bob@bob.com", "password": "bob"}, follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(session["user_id"], 1)
            self.assertEqual(session["search_history"], [])
            self.assertIn(b"Successfully logged in!", result.data)
            self.assertIn(b"Bob Bob", result.data)

    def test_user_login_password_failure(self):
        """Tests to see if user is redirected properly if password does not match"""
        result = self.client.post("/login", data={"email": "bob@bob.com", "password": "meep"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Incorrect username/password", result.data)
        self.assertIn(b"Login", result.data)

    def test_user_login_email_failure(self):
        """Tests to see if user is redirected properly is email is incorrect"""
        result = self.client.post("/login", data={"email": "meep", "password": "meep"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Incorrect username/password", result.data)
        self.assertIn(b"Login", result.data)

    def test_search_page(self):
        """Tests to see if search page renders properly"""
        result = self.client.get("/search")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Search", result.data)
        self.assertIn(b"Bob&#39;s Adventure", result.data)

    def test_user_info_page(self):
        """Tests to see if user info page renders properly, only showing data which is public"""
        result = self.client.get("/user/1")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Bob Bob", result.data)
        self.assertIn(b"Bob&#39;s First Adventure", result.data)
        self.assertIn(b"Bob&#39;s Adventure", result.data)
        self.assertNotIn(b"Favorite authors", result.data)
        self.assertNotIn(b"<h3> Update Profile </h3>", result.data)

    def test_user_info_dne(self):
        """Tests to see if user is redirected properly when attempting to go to page which doesn't exist"""
        result = self.client.get("/user/89208", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"User does not exist", result.data)
        self.assertIn(b"Homepage", result.data)

    def test_author_info_page_goodreads_id_series(self):
        """ Tests to see if author page properly displays if goodreads_id is present and they are connected to series"""
        with patch("wikipedia.page") as mock_page:
            mock_page.return_value.summary = "This author is cool"
            mock_page.return_value.images = ["Bob.jpg"]
            with patch("server.get_series_list_by_author") as mock_series:
                mock_series.return_value = {"1": "The Great Bob Adventure"}
                result = self.client.get("/author/1")

        self.assertEqual(result.status_code, 200)
        self.assertNotIn(b"Favorite this author", result.data)
        self.assertIn(b"Bob Bob", result.data)
        self.assertIn(b"This author is cool", result.data)
        self.assertIn(b"Bob.jpg", result.data)
        self.assertIn(b"The Great Bob Adventure", result.data)

    # might want to test what happens if goodreads_id is not present (no series)

    def test_author_info_page_no_series(self):
        """Tests to see if author page properly displays info if author has no series associated with them"""
        with patch("wikipedia.page") as mock_page:
            mock_page.return_value.summary = "This author is cool"
            mock_page.return_value.images = ["Bob.jpg"]
            with patch("server.get_series_list_by_author") as mock_series:
                mock_series.return_value = {}
                result = self.client.get("/author/1")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(b"Favorite this author", result.data)
        self.assertIn(b"Bob Bob", result.data)
        self.assertIn(b"This author is cool", result.data)
        self.assertIn(b"Bob.jpg", result.data)
        self.assertIn(b"No series", result.data)

    def test_author_info_page_dne(self):
        """Tests to see if user is redirected properly when attempting to access a page which does not exist"""
        result = self.client.get("/author/1829809", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Author does not exist", result.data)
        self.assertIn(b"Homepage", result.data)

    def test_series_info_page_dne(self):
        """Tests to see if user is redirected properly when attempting to access a page which does not exist"""
        result = self.client.get("/series/128909", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Series does not exist", result.data)
        self.assertIn(b"Homepage", result.data)

    def test_series_info_API_failure(self):
        """Tests to see if series info page renders properly if there is an API failure"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 400
            result = self.client.get("/series/1")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(b"Favorite this series", result.data)
        self.assertIn(b"Bob&#39;s Adventure", result.data)
        self.assertIn(b"Could not get info", result.data)

    def test_author_search_no_goodreads(self):
        """ Tests to see if user is redirected properly if searching by an author not in goodreads"""
        with patch("server.get_author_goodreads_info") as mock_response:
            mock_response.return_value = (None, None)
            result = self.client.post("/by-author", data={"author": "Nobody"}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Could not find", result.data)
        self.assertIn(b"Advanced Search", result.data)


class FlaskLoggedInTests(TestCase):
    """ Integration tests when users are logged in"""
    def setUp(self):
        """Sets up site for logged-in user"""
        self.client = app.test_client()
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "key"

        with self.client as c:
            with c.session_transaction() as sess:
                sess["user_id"] = 1
                sess["search_history"] = []
                # can add things to search history if needed

        connect_to_db(app, "postgresql:///testdb")
        db.create_all()
        example_data()

    def tearDown(self):
        """ Tear down to ensure database is the same for each test"""
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    def test_user_logout(self):
        """ Tests to make sure user logout works """
        with self.client as c:
            result = c.get("/logout", follow_redirects=True)
            self.assertNotIn("user_id", session)
            self.assertNotIn("search_history", session)
            self.assertEqual(result.status_code, 200)
            self.assertIn(b"Logged out", result.data)
            self.assertIn(b"Bibliofind", result.data)

    def test_own_user_info_page(self):
        """Tests to see if, when logged in, you see more info on your user page"""
        result = self.client.get("/user/1")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Bob Bob", result.data)
        self.assertIn(b"/author/1", result.data)
        self.assertIn(b"/series/1", result.data)
        self.assertIn(b"<h3> Update Profile </h3>", result.data)
        # should probably test to see if search results appear in here

    def test_another_user_info_page(self):
        """Tests to see if, when logged in, you cannot see certain things on other users' pages"""
        result = self.client.get("/user/2")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Jane Debugger", result.data)
        self.assertNotIn(b"/author/2", result.data)
        self.assertNotIn(b"<h3> Update Profile </h3>", result.data)

    def test_user_author_page_dne(self):
        """Tests to see if logged-in user gets redirected properly if attempting to access a page which does not exist"""
        result = self.client.get("/author/190890", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Author does not exist", result.data)
        self.assertIn(b"Bob Bob", result.data)

    def test_user_author_info_page_goodreads_id_series(self):
        """ Tests to see if author page properly displays if goodreads_id is present and they are connected to series"""
        with patch("wikipedia.page") as mock_page:
            mock_page.return_value.summary = "This author is cool"
            mock_page.return_value.images = ["Bob.jpg"]
            with patch("server.get_series_list_by_author") as mock_series:
                mock_series.return_value = {"1": "The Great Bob Adventure"}
                result = self.client.get("/author/1")

        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Favorite this author", result.data)
        self.assertIn(b"Bob Bob", result.data)
        self.assertIn(b"This author is cool", result.data)
        self.assertIn(b"Bob.jpg", result.data)
        self.assertIn(b"The Great Bob Adventure", result.data)

    # might want to test what happens if goodreads_id is not present (no series)

    def test_user_author_info_page_no_series(self):
        """Tests to see if author page properly displays info if author has no series associated with them"""
        with patch("wikipedia.page") as mock_page:
            mock_page.return_value.summary = "This author is cool"
            mock_page.return_value.images = ["Bob.jpg"]
            with patch("server.get_series_list_by_author") as mock_series:
                mock_series.return_value = {}
                result = self.client.get("/author/1")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Favorite this author", result.data)
        self.assertIn(b"Bob Bob", result.data)
        self.assertIn(b"This author is cool", result.data)
        self.assertIn(b"Bob.jpg", result.data)
        self.assertIn(b"No series", result.data)

    def test_user_series_page_dne(self):
        """Tests to see if logged-in user gets redirected properly when attempting to access a page that does not exist"""
        result = self.client.get("/series/1890", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Series does not exist", result.data)
        self.assertIn(b"Bob Bob", result.data)

    def test_user_user_page_dne(self):
        """Tests to see if logged in user gets redirectly properly when attempting to access a page that does not exist"""
        result = self.client.get("/user/18908", follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"User does not exist", result.data)
        self.assertIn(b"Bob Bob", result.data)

if __name__ == "__main__":
    main()
