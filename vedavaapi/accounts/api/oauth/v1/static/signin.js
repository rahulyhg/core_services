$(function() {
    queryParams = new URLSearchParams(document.location.search.substring(1));
    function signin() {
        let signinUrl = '../signin'
        let dataString = $('#login-form').serialize();
        $.ajax({
            type: 'POST',
            url: signinUrl,
            data: dataString,
            success: getConsent,
            error: function(xhr, status, error) {
                $("#login-success-status").text("log in failed.");
            }
        })
    }

    function getConsent() {
        let consentPageUrl = 'consent.html';
        if(queryParams.get('client_id')) {
            fullConsentUrl = `consent.html?${document.location.search.substring(1)}`;
            window.location.replace(fullConsentUrl);
        }
        else {
            $("#login-success-status").text("log in successfull.");
        }
    }

    $("#submit-button-login").click(signin);
})


