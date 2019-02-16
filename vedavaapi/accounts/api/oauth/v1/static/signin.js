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

    function oauthSignIn(providerName) {
        let oauthSignInUrl = `../oauth_signin/${providerName}`
        let consentPageUrl = getConsentUrl();
        let fullOauthSignInUrl = `${oauthSignInUrl}?redirect_url=${encodeURIComponent(consentPageUrl)}`;
        window.location.replace(fullOauthSignInUrl);
    }

    function googleSignIn() {
        oauthSignIn('google');
    }

    function absolutePath(href) {
        let link = document.createElement("a");
        link.href = href;
        return link.href;
    }

    function getConsentUrl() {
        let consentPageUrl = 'consent.html';
        let fullConsentUrl = `consent.html?${document.location.search.substring(1)}`;
        return absolutePath(fullConsentUrl);
    }

    function getConsent() {
        if(queryParams.get('client_id')) {
            //fullConsentUrl = `consent.html?${document.location.search.substring(1)}`;
            let fullConsentUrl = getConsentUrl();
            window.location.replace(fullConsentUrl);
        }
        else {
            $("#login-success-status").text("log in successful.");
        }
    }

    $("#submit-button-login").click(signin);
    $("#google_button").click(googleSignIn);
})
