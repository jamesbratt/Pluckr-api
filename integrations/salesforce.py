from datetime import timezone
import datetime
import requests
from django.conf import settings
from api.models import IntegrationAuth

SALESFORCE_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'

def salesforce_authentication(payload):
    payload = {
        'client_id': settings.SALESFORCE_CLIENT_ID,
        'client_secret': settings.SALESFORCE_CLIENT_SECRET,
        'code': payload['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': settings.SALESFORCE_REDIRECT_URI
    }
    response = requests.post(SALESFORCE_TOKEN_URL, verify=False, data=payload, headers={"Accept":"application/json"})
    if response.status_code is not 200:
        raise ValueError(response.json())
    return response.json()

def salesforce_proxy_request(url, key):
    integration = IntegrationAuth.objects.get(key=key)
    expiry_date = integration.req_date + datetime.timedelta(seconds=integration.expiry)
    if expiry_date < datetime.datetime.now(timezone.utc):
        # Get a new access token cause this ones expired
        raise ValueError('Expired access token')

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + integration.access_token}
    response = requests.get(url, headers=headers)
    if response.status_code is not 200:
        raise ValueError(response.json())
    return response.json()