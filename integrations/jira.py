import requests
from django.conf import settings
from api.models import IntegrationAuth, DataSource

JIRA_TOKEN_URL = 'https://auth.atlassian.com/oauth/token'

def jira_authentication(payload):
    payload = {
        'client_id': settings.JIRA_CLIENT_ID,
        'client_secret': settings.JIRA_CLIENT_SECRET,
        'code': payload['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': settings.JIRA_REDIRECT_URI
    }
    response = requests.post(JIRA_TOKEN_URL, data=payload, headers={"Accept":"application/json"})
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def jira_refresh(refresh_token):
    """ Not Implemented """
    return

def jira_request(url, token):
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def jira_proxy_request(url, key, source_id):
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')
   
    return jira_request(url, integration.access_token)
