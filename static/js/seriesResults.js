"use strict";
// Code for series result html


function showResults(result){
    // Displays results returned from AJAX call below
    if (result["status"] === "error"){
        alert("An error occurred. Please try again");
        $("#search-btn").html("Search");
    } else {
        $("#results-headline").show();
        let rPhrase;
        if (result["results"][0] === null) {
            rPhrase = "No books found in timeframe.";
        } else {
            rPhrase = `${result["results"][0]} <br> ${result["results"][1]}.`;
        }

        let seriesID = $('input[name=series]:checked').val();
        let IDAsString = `label[for=${seriesID}]`;
        let seriesName = $(IDAsString).text();

        let favButton = "Add " + seriesName + " to Favorites";
        $("#results-fav").text(favButton);
        $("#results-fav").show();

        $("#act-results").html("<img height='150' src='" + result["results"][2] + "'> <p>" + rPhrase + "</p>" );
        $("#results-email").show();
        $("#search-btn").html("Search");
        $("html, body").animate({ scrollTop: $(document).height() }, "slow"); 
    }
}

function searchSeries(evt){
    // sends an AJAX request to determine what the last book in a series 
    let seriesID = $('input[name=series]:checked').val();
    evt.preventDefault();
    if (seriesID === undefined){
        alert("Please select a series to search!");
    } else {
        $("#search-btn").html("<i class='fas fa-spinner fa-spin'></i>");
        $("#results-headline").hide();
        $("#results-fav").hide();
        $("#results-email").hide();
        $("#act-results").empty();
        let date = new Date();
        date = date.toDateString();
        let td = $("input[name=timeframe]:checked").val();
        let IDAsString = `label[for=${seriesID}]`;
        let seriesName = $(IDAsString).text();
        let formInputs = {'id': seriesID, 'name': seriesName, 'date': date, 'timeframe': td};
        $.post("/series-result.json", formInputs, showResults);
    }
}



$("#series-search").on("submit", searchSeries);

// when clicking on button, sends email to user with results.
$("#results-email").on("click", function(){
    let seriesID = $('input[name=series]:checked').val();
    let IDAsString = `label[for=${seriesID}]`;
    let seriesName = $(IDAsString).text();
    let title = "Bibliofind Search Results for " + seriesName;
    $("#results-email").html("<i class='fas fa-spinner fa-spin'></i>");
    let formInputs = {"result": $("#act-results").html(), "title": title};
    $.post("/email-info.json", formInputs, function(results){
        $("#results-email").html("Send Results to Email");
        alert(results["status"]);
    });

});

// on click, adds series to favorites
$("#results-fav").on("click", function(){
    let seriesID = $('input[name=series]:checked').val();
    let IDAsString = `label[for=${seriesID}]`;
    let seriesName = $(IDAsString).text();
    let formInput1 = {"series_name": seriesName};
    $.post("/get-series-id.json", formInput1, function(result1){
        if (result1["status"] !== "ok"){
            alert(result1["status"]);
        } else {
            let formInput2 = {"series_id": result1["id"]};
            $.post("/update-fav-series.json", formInput2, function(result2){
                alert(result2["result"]);
            });
        }
    });

});