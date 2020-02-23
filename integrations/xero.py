from datetime import timezone
import datetime
import base64
import requests
from django.conf import settings
from api.models import IntegrationAuth, DataSource

XERO_TOKEN_URL = 'https://identity.xero.com/connect/token'

def xero_authentication(payload):
    auth_header = settings.XERO_CLIENT_ID + ":" + settings.XERO_CLIENT_SECRET
    headers = {
        "Accept":"application/json",
        "Authorization": b"Basic " + base64.b64encode(auth_header.encode(encoding='utf_8'))
    }

    payload = {
        'code': payload['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': settings.XERO_REDIRECT_URI,
    }

    response = requests.post(XERO_TOKEN_URL, data=payload, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())

    json_response = response.json()

    tenant_headers = {
        "Accept":"application/json",
        "Authorization": "Bearer " + json_response['access_token'],
    }
    tenant_request = requests.get('https://api.xero.com/connections', headers=tenant_headers)
    if tenant_request.status_code != 200:
        raise ValueError(tenant_request.json())

    tenant_id = tenant_request.json()[0]['tenantId']
    json_response['tenantId'] = tenant_id
    return json_response

def xero_refresh(refresh_token):
    auth_header = settings.XERO_CLIENT_ID + ":" + settings.XERO_CLIENT_SECRET
    headers = {
        "Accept":"application/json",
        "Authorization": b"Basic " + base64.b64encode(auth_header.encode(encoding='utf_8'))
    }

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }

    response = requests.post(XERO_TOKEN_URL, data=payload, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def xero_request(url, token, tenant_id):
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + token,
        'Xero-tenant-id': tenant_id,
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()

def xero_proxy_request(url, key, source_id):
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')

    expiry_date = integration.req_date + datetime.timedelta(seconds=integration.expiry)
    if expiry_date > datetime.datetime.now(timezone.utc):

        # Get a new access token cause this ones expired
        refresh_token_response = xero_refresh(integration.refresh_token)
        new_req_date = datetime.datetime.now(timezone.utc)

        integration.access_token = refresh_token_response['access_token']
        integration.req_date = new_req_date
        integration.save()
        return xero_request(url, refresh_token_response['access_token'], integration.tenantId)
    return xero_request(url, integration.access_token, integration.tenantId)
