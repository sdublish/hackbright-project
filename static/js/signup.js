// Javascript for signup-page
"use strict";


// on signup up, check if passwords match
// if not, prevent submission and post alert to user.
$("#sign-up").on("submit", function(evt){
    let pw = $("#password").val();
    let pw2 = $("#password2").val();
    if (pw !== pw2){
        evt.preventDefault();
        alert("Passwords do not match. Please try again.");
    }
});