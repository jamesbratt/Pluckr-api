import datetime, requests
from cryptography.fernet import Fernet
from integrations.facebook import facebook_authentication
from api.models import IntegrationAuth

def integrate(integration_type, payload, request):
    if integration_type == 'facebook':
        auth_response = facebook_authentication(payload)
        if auth_response:
            expires_in = auth_response['expires_in']
            req_date = datetime.datetime.now()
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                key=auth_key,
                access_token=auth_response['access_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return { 'key': auth_key, 'expiry': expiry_date, 'provider': integration_type }

def integrateRequest(url, key):
    token = IntegrationAuth.objects.get(key=key)
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers, verify=False)
    if response.status_code is not 200:
        raise ValueError(response.json())
    return response.json()
