"use strict";
// code for advanced-search page


// when author button is clicked, show form to search for author
$("#author-btn").on("click", function(){
    $("#author-search").show();
    $("#title-search").hide();
});

// when title button is clicked, show form to search by book title
$("#title-btn").on("click", function(){
    $("#author-search").hide();
    $("#title-search").show();
});