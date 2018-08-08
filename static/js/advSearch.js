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

// on form submission, change search button into a loading wheel
$("#author-search-frm").on("submit", function(){
    $("#author-search-btn").html("<i class='fas fa-spinner fa-spin'></i>");
});

// on form submission, change search button into a loading wheel
$("#title-search-frm").on("submit", function(){
    $("#title-search-btn").html("<i class='fas fa-spinner fa-spin'></i>");
});