"use strict";
// Code for search page.


// on click, shows form with fields related to searching by author
$("#search-author").on("click", function(){
    $("#search-history").val("author");
    $("#search").show();
    $("#author-field").show();
    $("#series-field").hide();
    $('.selectpicker').selectpicker('val', '');
    $("#results").text("");
});

// on click, shows for with fields related to searching by series
$("#search-series").on("click", function(){
    $("#search-history").val("series");
    $("#search").show();
    $("#author-field").hide();
    $("#series-field").show();
    $("#author").val("");
    $("#results").text("");
});


// on click, sends results of search to email with AJAX request
$("#results-email").on("click", function(){
    let title;
    if ($("#search-history").val() === 'author') {
        title = $("#author").val(); 
    } else if ($("#search-history").val() === 'series') {
        title = $("#series").val();
    }
    title = "Bibliofind Search Results for " + title;
    let formInputs = {"result": $("#act-results").html(), "title": title};
    $.post("/email-info.json", formInputs, function(results){
        alert(results["status"]);
    });

});

// on click, adds search value to favorites
$("#results-fav").on("click", function(){
    if ($("#search-history").val() === 'series'){
        let formInputs = {"series_id": $("#series").val()};

        $.post("/update-fav-series.json", formInputs, function(results){
            alert(results.result);
        });
    } else {
        // get the name of the author
        // strip of any whitetext?
        // send this to a route
        // check to see if author is in database
        // ... which will be difficult, because of goodreads
        // so things I can do:
        // query goodreads to see if author name comes up with ID
        // if no ID comes up, well, assume not in goodreads and handle from there
        // if there is an ID, check to see if that id is already taken in the database
        // if so, use that to add favorite and do all that check
        // if 
        console.log("Need to implement this");
    }

});

// on click, checks to see if a value has been inputted. If it has, sends an AJAX
// request to figure out what book to show, and then shows the results.
$("#search").on("submit", function(evt){
    evt.preventDefault();
    let author = $("#author").val();
    let series = $("#series").val();

    if (author && series) {
        $("#results").text("Please enter only an author or a series, not both.");
    } else if (!author && !series) {
        $("#results").text("Please enter a value to submit!");
    } else{
        $("#results").text("Searching...")
        $("#results-headline").show();
        let date = new Date();
        date = date.toDateString();
        let td = $("input[name=timeframe]:checked").val();
        let formInputs = {"date": date, "author": author, "series": series, "timeframe" : td};
        $.post("/search.json", formInputs, function(result){
            let mrPhrase = `Most recently released: ${result.most_recent[0]}, publication date: ${result.most_recent[1]}`;
            let rPhrase;
            if (result.results[0] === null) {
            rPhrase = "No books found in timeframe.";
            } else {
            rPhrase = `Results: ${result.results[0]}, publication date: ${result.results[1]}.`;
            }

            $("#most-recent").html("<h4>Most Recent</h4><img height='200' src='" + result.most_recent[2] + "'> <p>" + mrPhrase + "</p>" )
            $("#act-results").html("<h4> Result in Timeframe </h4><img height='200' src='" + result.results[2] + "'> <p>" + rPhrase + "</p>" )

            $("#results-email").show();
            let favButton;
            if ($("#search-history").val() === 'author') {
                favButton = "Add " + $("#author").val() + " to Favorites";
            } else if ($("#search-history").val() === 'series') {
                favButton = "Add " + $("#series option:selected").text() + " to Favorites";
            }
            $("#results-fav").text(favButton);
            $("#results-fav").show();
            $("#results").text("");
            $("html, body").animate({ scrollTop: $(document).height() }, "slow");

        });
    }

});
