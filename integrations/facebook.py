import requests
import datetime
from datetime import timezone
from api.models import IntegrationAuth, DataSource
from django.conf import settings

FACEBOOK_TOKEN_URL = 'https://graph.facebook.com/v3.3/oauth/access_token'

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

def facebook_proxy_request(url, key, source_id):
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')

    expiry_date = integration.req_date + datetime.timedelta(seconds=integration.expiry)
    if expiry_date < datetime.datetime.now(timezone.utc):
        # Get a new access token cause this ones expired
        raise ValueError('Expired access token')

    accesstoken_key_string = '?access_token=' if '?' not in url else '&access_token='

    url_with_token = url + accesstoken_key_string + integration.access_token

    headers = {'Content-Type': 'application/json'}
    response = requests.get(url_with_token, headers=headers, verify=False)
    if response.status_code is not 200:
        raise ValueError(response.json())
    return response.json()