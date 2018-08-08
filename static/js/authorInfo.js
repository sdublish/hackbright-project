"use strict";

// on click, favorites author for user 
$("#fav-author").on("submit", function(evt){
    evt.preventDefault();
    let formInputs = {"author_id": $("#author-id").val() };
    $.post("/update-fav-author.json", formInputs, function(results){
        alert(results.result);
    });
});

// on clicking the Goodreads favorite button, shows a spinner to indicate stuff is happening behind the scenes
$("#gr-fav-btn").on("click", function(){
    $("#gr-fav-btn").html("<i class='fas fa-spinner fa-spin'></i>");
})