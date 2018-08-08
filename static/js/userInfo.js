"use strict";
// Code for user info page

// on click on any link in favorite author list, shows spinner until page loads
$("#user-fav-author").on("click", "a", function(){
    $('#cover-spin').show(0);
})

// on click on any link in favorite series list, shows spinner until page loads
$("#user-fav-series").on("click", "a", function(){
    $('#cover-spin').show(0);
})

// on click, shows form to update profile
$("#update-profile-btn").on("click", function(){
    $("#update-profile-form").show();
    $("#update-fs-form").hide();
    $("#update-fa-form").hide();
    $("html, body").animate({ scrollTop: $(document).height() }, "slow");

});


// on click, shows form to update favorite series
$("#update-fs-btn").on("click", function(){
    $("#update-profile-form").hide();
    $("#update-fs-form").show();
    $("#update-fa-form").hide();
    $("html, body").animate({ scrollTop: $(document).height() }, "slow");

});

// on click, shows form to update favorite authors
$("#update-fa-btn").on("click", function(){
    $("#update-profile-form").hide();
    $("#update-fs-form").hide();
    $("#update-fa-form").show();
    $("html, body").animate({ scrollTop: $(document).height() }, "slow");

});

// on click, toggles display of search history and modifies button text value
// to match current state
$("#search-history-display").on("click", function(){
    $("#search-history-table").toggle();
    $("#send-search-history").toggle();
    if ($("#search-history-display").text() === 'Hide Search History'){
        $("#search-history-display").text('Show Search History');
    } else {
        $("#search-history-display").text('Hide Search History');
    }
});

// sends an AJAX request so search history can be emailed to user
$("#send-search-history").on("click", function(){
    let title = 'Your Search History';
    let searchHistory = $("#search-history").html();
    let formInputs = {"title": title, "result": searchHistory};
    $.post("/email-info.json", formInputs, function(results){
        alert(results["status"]);
    })
})