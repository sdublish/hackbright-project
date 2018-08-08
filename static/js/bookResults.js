"use strict";
// code for book-results html page

// on click, checks to see if book is picked
// if not, alerts user to pick a book
// otherwise, turns search button into spinner
$("#book-search-form").on("submit", function(evt){
    let bookName = $('input[name=book]:checked').val();
    if (bookName === undefined){
        evt.preventDefault();
        alert('Please select a book to search by!');
    } else {
        $("#book-search-btn").html("<i class='fas fa-spinner fa-spin'></i>");
    }
});