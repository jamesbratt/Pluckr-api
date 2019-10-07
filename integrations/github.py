from datetime import timezone
import datetime
import requests
from django.conf import settings
from api.models import IntegrationAuth, DataSource

GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
PAGE_LIMIT = 100
REQUEST_LIMIT = 10

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

def github_request(url, token, responses = [], page = 1):
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    if page > REQUEST_LIMIT:
        raise ValueError('Too many page requests required, try making your request more specific by applying parameters')
    if len(response.json()) == PAGE_LIMIT:
        page_param = '&page=' + str(page + 1)
        return github_request(url + page_param, token, responses + response.json(), page + 1)
    else:
        return responses + response.json()

def github_proxy_request(url, key, source_id):
    pages = 0
    if key is not None:
        integration = IntegrationAuth.objects.get(key=key)

    if key is None and source_id is not None:
        integration = DataSource.objects.get(pk=source_id).integration_auth
        pages = DataSource.objects.get(pk=source_id).pages

    if key is None and source_id is None:
        raise ValueError('Unable to retrieve integration token')

    if pages == 0:
        return github_request(url, integration.access_token)
    else:
        concatenated_responses = []
        for page in range(pages + 1):
            if page != 0:
                page_param = '&page=' + str(page)
                req = github_request(url + page_param, integration.access_token)
                concatenated_responses = concatenated_responses + req
        return concatenated_responses
  