from integrations.facebook import facebook_authentication

def integrate(integration_type, payload):
    if integration_type == 'facebook':
        return facebook_authentication(payload)

    return payload

