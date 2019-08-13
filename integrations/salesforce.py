from datetime import timezone
import datetime
import requests
from django.conf import settings
from api.models import IntegrationAuth, DataSource

SALESFORCE_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'

def salesforce_authentication(payload):
    payload = {
        'client_id': settings.SALESFORCE_CLIENT_ID,
        'client_secret': settings.SALESFORCE_CLIENT_SECRET,
        'code': payload['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': settings.SALESFORCE_REDIRECT_URI
    }
    response = requests.post(SALESFORCE_TOKEN_URL, data=payload, headers={"Accept":"application/json"})
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def salesforce_refresh(refresh_token):
    params = '?grant_type=refresh_token&client_id=' + settings.SALESFORCE_CLIENT_ID + '&client_secret=' + settings.SALESFORCE_CLIENT_SECRET + '&refresh_token=' + refresh_token
    response = requests.post(SALESFORCE_TOKEN_URL + params, headers={"Accept":"application/json"})
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def salesforce_request(url, token):
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def salesforce_proxy_request(url, key, source_id):
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')
   
    expiry_date = integration.req_date + datetime.timedelta(seconds=integration.expiry)
    if expiry_date < datetime.datetime.now(timezone.utc):

        # Get a new access token cause this ones expired
        refresh_token_response = salesforce_refresh(integration.refresh_token)
        new_req_date = datetime.datetime.now(timezone.utc)

        integration.access_token = refresh_token_response['access_token']
        integration.req_date = new_req_date
        integration.save()
        return salesforce_request(url, refresh_token_response['access_token'])
    return salesforce_request(url, integration.access_token)
