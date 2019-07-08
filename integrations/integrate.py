import requests
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from integrations.facebook import facebook_authentication
from api.models import IntegrationAuth

def integrate(integration_type, payload, request):
    if integration_type == 'facebook':
        auth_response = facebook_authentication(payload)
        if auth_response:
            expires_in = auth_response['expires_in']
            req_date = datetime.datetime.now(timezone.utc)
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return { 'key': auth_key, 'expiry': expiry_date, 'provider': integration_type }

def integrateRequest(url, key):
    integration = IntegrationAuth.objects.get(key=key)
    expiry_date = integration.req_date + datetime.timedelta(seconds=integration.expiry)
    if expiry_date < datetime.datetime.now(timezone.utc):
        # Get a new access token cause this ones expired
        raise ValueError('Expired access token')

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + integration.access_token}
    response = requests.get(url, headers, verify=False)
    if response.status_code is not 200:
        raise ValueError(response.json())
    return response.json()
