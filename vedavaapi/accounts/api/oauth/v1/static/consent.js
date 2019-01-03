$(function() {
    queryParams = new URLSearchParams(document.location.search.substring(1));
    authRequestData = {};
    for(let param of queryParams) {
        authRequestData[param[0]] = param[1];
    }

    $('#consent-info-client_id').text(queryParams.get('client_id'));
    $('#consent-info-scopes').text(String(queryParams.get('scope') || '').split(' '));

    function postConsent() {
        let consentUrl = '../authorize';
        $.ajax({
            type: 'POST',
            url: consentUrl,
            data: authRequestData,
            success: onSuccess
        });
    }

    function onSuccess(res) {
        $('body').html(res);
    }

    $('#consent-form-submit').click(postConsent);
})
