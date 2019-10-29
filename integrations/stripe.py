import requests
from django.conf import settings
from api.models import IntegrationAuth, DataSource

STRIPE_TOKEN_URL = 'https://connect.stripe.com/oauth/token'

def stripe_authentication(payload):
    payload = {
        'client_secret': settings.STRIPE_CLIENT_SECRET,
        'code': payload['code'],
        'grant_type': 'authorization_code',
    }
    response = requests.post(STRIPE_TOKEN_URL, data=payload, headers={"Accept":"application/json"})
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def stripe_request(url, token):
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def stripe_proxy_request(url, key, source_id):
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')

    return stripe_request(url, integration.access_token)
