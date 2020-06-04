import time
import requests
from django.conf import settings

def generate_url(endpoint, params):
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i is 0 and '?' not in url:
            symbol = '?'
        url += str(symbol + param_key + '=' + param)
    return url

def finance_proxy_request(url, retry = True):
    headers = {'Content-Type': 'application/json'}
    url_with_token = generate_url(url, [('token', settings.STOCK_MARKET_API_KEY)])
    response = requests.get(url_with_token, headers=headers)
    if response.status_code != 200:
        if retry is True:
            time.sleep(1)
            return finance_proxy_request(url, False)
        raise ValueError(response.json())
    return response.json()
