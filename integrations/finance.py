import requests

def finance_proxy_request(url):

    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(response.json())
    return response.json()
