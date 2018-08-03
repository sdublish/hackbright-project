"use strict";
// Code for series info page

// on click, favorites series
$("#fav-series").on("submit", function(evt){
    evt.preventDefault();
    let formInputs = {"series_id": $("#series-id").val() };

    $.post("/update-fav-series.json", formInputs, function(results){
        alert(results.result);
    });
});