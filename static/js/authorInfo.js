"use strict";

// on click, favorites author for user 
$("#fav-author").on("submit", function(evt){
    evt.preventDefault();
    let formInputs = {"author_id": $("#author-id").val() };
    $.post("/update-fav-author.json", formInputs, function(results){
        alert(results.result);
    });
});