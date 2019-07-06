import requests
from django.conf import settings

FACEBOOK_TOKEN_URL = 'https://graph.facebook.com/v3.3/oauth/access_token';

def generate_url(endpoint, params):
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i is 0:
            symbol = '?'
        url += str(symbol + param_key + '=' + param)
    return url


def facebook_authentication(payload):

    params = [
        ('client_id', settings.FACEBOOK_CLIENT_ID),
        ('redirect_uri', settings.FACEBOOK_REDIRECT_URI),
        ('client_secret', settings.FACEBOOK_CLIENT_SECRET),
        ('code', payload['code']),
    ]

    url = generate_url(FACEBOOK_TOKEN_URL, params)

    response = requests.get(url, verify=False)
    if response.status_code is not 200:
        raise ValueError(response.json())
    return response.json()