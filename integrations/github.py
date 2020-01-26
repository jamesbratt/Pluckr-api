from datetime import timezone
import datetime
import requests
from django.conf import settings
from api.models import IntegrationAuth, DataSource

GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
PAGE_LIMIT = 100
REQUEST_LIMIT = 10

def generate_url(endpoint, params):
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i is 0 and '?' not in url:
            symbol = '?'
        url += str(symbol + param_key + '=' + param)
    return url

def github_authentication(payload):
    payload = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': payload['code'],
    }
    response = requests.post(GITHUB_TOKEN_URL, data=payload, headers={"Accept":"application/json"})
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def github_request(url, token):
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def github_proxy_request(url, key, source_id):
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')

    finalUrl = generate_url(url, [('per_page', '100')])
    return github_request(finalUrl, integration.access_token)
