# Bibliofind
## Summary
Bibliofind helps users find out when the next book  from their favorite author or series will be published.  After inputting a series or author name, the application gathers the necessary information from the Goodreads or Google Books API, and displays the information for the user.   If a series is not in the application database, users can use the advanced search option to get to a series name by searching by author or book title. Users who have made an account can email these results, and their search history, directly to their email. In addition, registered users can link their Goodreads account to their Bibliofind account, and directly favorite authors for their Goodreads account via Bibliofind.

## Tech Stack
**Frontend**: HTML5, CSS, Javascript, jQuery, Bootstrap, Bootstrap-Select
**Backend**: Python, Flask, PostgreSQL, SQLAlchemy, Flask-Mail, Jinja, rauth
**APIs**: Goodreads, Google Books, Wikipedia

## Features
Visitors can use the site with or without an account. Without an account, visitors can search for when the next book is coming out by series name or author. 
![Alt text](/static/img/example.gif?raw=true "Searching on Bibliofind")

If the series is not available in the database, users can go to advanced search, which allows them to find a series by author name or book title. As soon as they search for a specific series, it is added to the database, making it easier to search in the future.

With an account, users can track their favorite authors and series. Doing so allows the user to quickly search for those items in the search function.

After getting the search results, a logged-in user can also add the author or series to their favorites list directly. They can also email the search results (the cover, book title, and publication date) to the email they registered under.

On the profile page, users can add authors and series to their favorites list, and link their account to Goodreads. They are also provided a link to an informational page aobut their favorite author and series. 

On the author page, users are presented with a brief summary of the author, as well as a list of series they are associated with on Goodreads. If an user is logged and has given Bibliofind the permission to access their Goodreads account, they can follow the author on Goodreads by clicking on a button on Bibliofind.

## Planned Features
* Allow users to input any time frame when searching for books
* Allow users to add books to their Goodreads shelf directly from the series page
* Add links to the info pages of authors and series on search result page
* Allow users to link their Google Books account to their Bibliofind account