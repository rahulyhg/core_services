from .v1.authorization_ns import api, TokenResolver


def get_token_resolver_uri():
    return api.url_for(TokenResolver, _external=True)
