""" Tests for project """

from unittest import TestCase, main
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import patch

from server import app
from model import connect_to_db
from goodreads_util import (sort_series, get_info_for_work, get_author_goodreads_info,
                            get_series_list_by_author)
from google_util import get_pub_date_with_book_id
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

    def test_strip_tags(self):
        """Tests strip_tags functionality"""
        test_str = "<b> Look at this <i>test</i> string! </b>"
        self.assertEqual(strip_tags(test_str).strip(), "Look at this test string!")


class GoogleUtilTests(TestCase):
    """Testing Google Books Utility Functions"""
    def test_pub_date_with_book_id(self):
        with patch('requests.get') as mock_request:
            mock_request.return_value.json.return_value = {"volumeInfo": {"publishedDate": "2016-07-07"}}
            self.assertEqual("2016-07-07", get_pub_date_with_book_id("1"))
    # how would I test the get pub date with title, since that basically just gets the id number and goes from there?


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
        """Tests to see if sort_series returns a dictionary with the right id when passed in two series"""
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
        </best_book>
        <original_publication_year/>
        <original_publication_month/>
        <original_publication_day/>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "A Test?!", "published": None, "author": "Bob Smith"})

    def test_get_info_for_work_year(self):
        """Tests to see if get_info_for_work returns info when given publication year"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>Test</title>
        <author> <name>Bob Bob</name></author>
        </best_book>
        <original_publication_year>2016</original_publication_year>
        <original_publication_month/>
        <original_publication_day/>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "Test", "published": "2016", "author": "Bob Bob"})

    def test_get_info_for_work_year_mon(self):
        """Tests to see if get_info_for_work gives results if work has publication month and year"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>Test 2</title>
        <author> <name>Smith Bob</name></author>
        </best_book>
        <original_publication_year>2016</original_publication_year>
        <original_publication_month>3</original_publication_month>
        <original_publication_day/>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "Test 2", "published": "2016-03", "author": "Smith Bob"})

    def test_get_info_for_work_year_mon_day(self):
        """Tests to see if get_info_for_work works if all publication info is given"""
        test_xml = """<series_work>
        <work>
        <best_book>
        <title>George's Best Day</title>
        <author> <name>George Gold</name></author>
        </best_book>
        <original_publication_year>2016</original_publication_year>
        <original_publication_month>4</original_publication_month>
        <original_publication_day>9</original_publication_day>
        </work>
        </series_work> """
        test_work = ET.fromstring(test_xml)
        self.assertEqual(get_info_for_work(test_work), {"title": "George's Best Day", "published": "2016-04-09", "author": "George Gold"})

    def test_author_goodreads_info_error(self):
        """ Checks to see if function returns (None, None) when status code is not 200"""
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 400
            self.assertEqual((None, None), get_author_goodreads_info("Doesn't Exist"))

    # check to see how author_goodreads_info handles stuff when status = 200 but no author info is available?

    def test_author_goodreads_info_exists(self):
        """ Checks to see if function returns proper info when status code is 200"""
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<Goodreads><author id='40'><name>John Doe</name></author></Goodreads>"
            self.assertEqual(("40", "John Doe"), get_author_goodreads_info("John Doe"))

    def test_get_series_list_by_author_error(self):
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 400
            self.assertIsNone(get_series_list_by_author(1))

    def test_get_series_list_by_author_no_series(self):
        with patch("requests.get") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.content = "<series> </series>"
            self.assertEqual({}, get_series_list_by_author(1))


class FlaskNotLoggedInTests(TestCase):
    """ Integration tests for when user is not logged in"""
    # check to see if log-in button appears? or is that a different kind of test?
    def setUp(self):
        """Sets up app for a not-logged in user"""
        self.client = app.test_client()
        app.config["TESTING"] = True

        connect_to_db(app, "postgresql:///testdb")
        # then create tables and add sample data

    # define teardown function

    def test_homepage(self):
        """ Tests to see if homepage renders properly"""
        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"<h1> Project Homepage </h1>", result.data)

    def test_login_page(self):
        """ Tests to see if login page renders properly"""
        result = self.client.get("/login")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"<h1> Login </h1>", result.data)

    def test_signup_page(self):
        """ Tests to see if signup page renders properly"""
        result = self.client.get("/sign-up")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"<h1> Sign Up </h1>", result.data)


class FlaskLoggedInTests(TestCase):
    """ Integration Tests when users are logged in"""
    # check to see if logged-out button is there?
    def setUp(self):
        """Sets up site for logged-in user"""
        self.client = app.test_client()
        app.config["TESTING"] = True

        connect_to_db(app, "postgresql:///testdb")
        # then create tables and add sample data

    # define teardown function

if __name__ == "__main__":
    main()
