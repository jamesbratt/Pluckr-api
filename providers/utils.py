""" Generic utilities for providers """

import requests

def generate_url(endpoint, params):
    """ Building the oauth authorisation url """
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i is 0:
            symbol = '?'
        url += str(symbol + param_key + '=' + param)
    return url

class Connection:
    """ Establishing a connection with a provider """

    v2_auth_types = ["basic", "apiKey", "oauth2"]

    def __init__(self, request, security_definition):
        self.request = request
        self.security_definition = security_definition
        self.spec_version = security_definition["swagger"]

class V2OpenApiSpecConnection(Connection):
    v2_auth_types = ["basic", "apiKey", "oauth2"]

    def invoke_auth_flow(self):
        definition_type = self.security_definition["type"]

        if definition_type == "basic":
            return

        if definition_type == "apiKey":
            return

        if definition_type == "oauth2":
            return

        return self

class Swagger:
    """ Interacting with Swagger """

    def __init__(self, swagger_url):
        self.swagger_url = swagger_url
        self.definition = self.fetch_definition()

    def fetch_definition(self):
        """ Making an HTTP request for a swagger definition """
        response = requests.get(self.swagger_url)
        if response.status_code != 200:
            raise ValueError(response.json())

        return response.json()

    def extract_security_definition(self):
        """ Return the security defintion only """
        key = list(self.definition['securityDefinitions'])[0]
        return self.definition['securityDefinitions'][key]
