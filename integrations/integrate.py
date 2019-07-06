import datetime
from integrations.facebook import facebook_authentication
from api.models import IntegrationAuth

def integrate(integration_type, payload):
    if integration_type == 'facebook':
        auth_response = facebook_authentication(payload)
        if auth_response:
            req_date = datetime.datetime.now()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                access_token=auth_response['access_token'],
                expiry=auth_response['expires_in'],
                req_date=req_date,
                user=req_date,
            )
            integration_creds.save()

    return payload

