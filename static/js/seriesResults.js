"use strict";
// Code for series result html


function showResults(result){
    // Displays results returned from AJAX call below
    let mrPhrase = `Most recently released: ${result.most_recent[0]}, publication date: ${result.most_recent[1]}`;
    let rPhrase;
    if (result.results[0] === null) {
    rPhrase = "No books found in timeframe.";
    } else {
    rPhrase = `Results: ${result.results[0]}, publication date: ${result.results[1]}.`;
    }

    $("#most-recent").html("<h4>Most Recent</h4><img height='200' src='" + result.most_recent[2] + "'> <p>" + mrPhrase + "</p>" );
    $("#act-results").html("<h4> Result in Timeframe </h4><img height='200' src='" + result.results[2] + "'> <p>" + rPhrase + "</p>" );
    $("#results-email").show();

}

function searchSeries(evt){
    // sends an AJAX request to determine what the last book in a series is
    evt.preventDefault();
    let date = new Date();
    date = date.toDateString();
    let td = $("input[name=timeframe]:checked").val();
    let seriesID = $('input[name=series]:checked').val();
    let IDAsString = `label[for=${seriesID}]`;
    let seriesName = $(IDAsString).text();
    let formInputs = {'id': seriesID, 'name': seriesName, 'date': date, 'timeframe': td};
    $("#results-headline").show();
    $.post("/series-result.json", formInputs, showResults);
}



$("#series-search").on("submit", searchSeries);

// when clicking on button, sends email to user with results.
$("#results-email").on("click", function(){
    let seriesID = $('input[name=series]:checked').val();
    let IDAsString = `label[for=${seriesID}]`;
    let seriesName = $(IDAsString).text();
    let title = "Bibliofind Search Results for " + seriesName;
    let formInputs = {"result": $("#act-results").html(), "title": title};
    $.post("/email-info.json", formInputs, function(results){
        alert(results["status"]);
    });

});