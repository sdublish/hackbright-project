from unittest import TestCase, main
import xml.etree.ElementTree as ET
from datetime import datetime

from server import app
from model import connect_to_db
from goodreads_util import sort_series, get_info_for_work
from server_util import convert_string_to_datetime, strip_tags


class ServerUtilTests(TestCase):
    """ Testing server utility functions """
    def test_convert_datetime_year(self):
        """ Makes sure function turns a string with year-only into a datetime object"""
        self.assertEqual(convert_string_to_datetime("2016"), datetime(year=2016, month=1, day=1))

    def test_convert_datetime_year_mon(self):
        self.assertEqual(convert_string_to_datetime("2016-02"), datetime(year=2016, month=2, day=1))

    def test_convert_datetime_year_mon_day(self):
        self.assertEqual(convert_string_to_datetime("2016-02-02"), datetime(year=2016, month=2, day=2))

    def test_strip_tags(self):
        """Tests strip_tags functionality"""
        test_str = "<b> Look at this <i>test</i> string! </b>"
        self.assertEqual(strip_tags(test_str).strip(), "Look at this test string!")


class GoogleUtilTests(TestCase):
    # not sure I need to test anything currently in this file
    # right now, both functions are basically simple API calls
    # then again, important to test all functions, no matter how small
    # i guess i'm getting stuck on the HOW then
    pass


class GoodreadsUtilTests(TestCase):
    def test_sort_series_zero_series(self):
        self.assertEqual(sort_series([]), {})

    def test_sort_series_one_series(self):
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


class FlaskTests(TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

        connect_to_db(app, "postgresql:///testdb")
        # then create tables and add sample data

    def test_homepage(self):
        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"<h1> Project Homepage </h1>", result.data)


if __name__ == "__main__":
    main()
