from datetime import timezone
import datetime
import requests
from django.conf import settings
from api.models import IntegrationAuth

GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'

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

def github_proxy_request(url, key):
    integration = IntegrationAuth.objects.get(key=key)
    return github_request(url, integration.access_token)