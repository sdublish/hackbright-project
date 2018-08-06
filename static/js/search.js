"use strict";
// Code for search page.


// on click, shows form with fields related to searching by author
$("#search-author").on("click", function(){
    $("#search-history").val("author");
    $("#search").show();
    $("#author-field").show();
    $("#fav-author-field").show();
    $("#series-field").hide();
    $("#fav-series-field").hide();
    $('.selectpicker').selectpicker('val', '');
    $("#results").text("");
});

// on click, shows for with fields related to searching by series
$("#search-series").on("click", function(){
    $("#search-history").val("series");
    $("#search").show();
    $("#author-field").hide();
    $("#fav-author-field").hide();
    $("#series-field").show();
    $("#fav-series-field").show();
    $("#author").val("");
    $("#results").text("");
});

// when user changes series in series field, and it does not match what is in favorite series
// sets value of favorite series to empty string
$("#series").on("changed.bs.select", function(e, clickedIndex, isSelected, previousValue){
    if ($(this).find("option").eq(clickedIndex).val() !== $("#fav-series").val()){
        $("#fav-series").val("");
        $(".selectpicker").selectpicker('render');
    }
});


// when user picks favorite series, sets value in series field to match
$("#fav-series").on("changed.bs.select", function(e, clickedIndex, isSelected, previousValue){
    let series = $(this).find('option').eq(clickedIndex).val();
    $("#series").val(series);
    $(".selectpicker").selectpicker('render');

});


// when user changes author in author field, and it does not match what is in favorite author
// sets value of favorite author to empty string
$("#author").on("change", function(){
    if ( $("#author").val() !== $("#fav-auth").val()){
        $("#fav-auth").val("");
        $(".selectpicker").selectpicker('render');
    }
})

// when user picks favorite author, sets value in author field to match
$("#fav-auth").on("changed.bs.select", function(e, clickedIndex, isSelected, previousValue){
    let author = $(this).find('option').eq(clickedIndex).val();
    $("#author").val(author);
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
        let formInputs1 = {"author" :$("#author").val()};
        $.post("/get-author-id.json", formInputs1, function(results){
            if (results["auth_status"] === "ok"){
                let formInputs2 = {"author_id": results["id"]}
                $.post("/update-fav-author.json", formInputs2, function(result){
                    alert(result.result);
                });
            } else {
                alert("Cannot add this author to favorites at this time. Sorry!");
            }

        });
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
            if (result["status"] === "error"){
                alert("An error occured. Please try again.");
            } else {
                let rPhrase;
                if (result.results[0] === null) {
                rPhrase = "No books found in timeframe.";
                } else {
                rPhrase = `Results: ${result.results[0]}, publication date: ${result.results[1]}.`;
                }

                $("#act-results").html("<img height='200' src='" + result.results[2] + "'> <p>" + rPhrase + "</p>" )

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
            }
        });
    }
});
