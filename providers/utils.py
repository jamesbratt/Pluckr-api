""" Generic utilities for providers """

from datetime import timezone
import datetime
import requests
from cryptography.fernet import Fernet

from api.models import IntegrationAuth

def generate_url(endpoint, params):
    """ Building the oauth authorisation url """
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i == 0:
            symbol = '?'
        url += str(symbol + param_key + '=' + param)
    return url

class Connection:
    """ Establishing a connection with a provider """

    def __init__(self, request, security_definition, provider):
        self.request = request
        self.security_definition = security_definition
        # self.spec_version = security_definition["swagger"]
        self.provider = provider

    def create_connection(self, auth_response):
        """ Create an integration object and link it to the provider """

        expires_in = auth_response['expires_in']
        req_date = datetime.datetime.now(timezone.utc)
        auth_key = Fernet.generate_key()
        integration_creds = IntegrationAuth(
            integration_type=self.provider.name,
            refresh_token=auth_response['refresh_token'],
            key=auth_key.decode("utf-8"),
            access_token=auth_response['access_token'],
            expiry=expires_in,
            req_date=req_date,
            user=self.provider.user,
        )
        integration_creds.save()
        self.provider.connection = integration_creds
        self.provider.save()

    def fetch_oauth_token(self, token_url, code):
        """ Making an http request for an oauth token """

        payload = {
            'client_id': self.provider.client_id,
            'client_secret': self.provider.client_secret,
            'code': code,
            'redirect_uri': 'http://localhost:8000/providers/authorize/' + str(self.provider.id) + '/'
        }

        response = requests.post(token_url, data=payload, headers={"Accept":"application/json"})
        if response.status_code != 200:
            raise ValueError(response.json())
        return response.json()

    def invoke_password_flow(self):
        """ Handling the password flow """
        return

    def invoke_implicit_flow(self):
        """ Handling the implicit flow """
        return

    def invoke_application_flow(self):
        """ Handling the application flow """
        return

    def invoke_access_code_flow(self):
        """ Handling the access code flow """

        code = self.request.GET['code']
        token_url = self.security_definition["tokenUrl"]

        if code is None:
            raise ValueError("No access code has been supplied")

        if token_url is None:
            raise ValueError("No token url has been defined in the definition")

        return self.fetch_oauth_token(token_url, code)

class V2OpenApiSpecConnection(Connection):
    """ Connecting to an api with a v2 defintion """

    implict_flow = "implicit"
    password_flow = "password"
    application_flow = "application"
    access_code_flow = "accessCode"

    v2_auth_flows = [implict_flow, password_flow, application_flow, access_code_flow]

    def invoke_auth_flow(self):
        """ Determine how to handle the connection """

        definition_type = self.security_definition["type"]
        definition_flow = self.security_definition["flow"]

        if definition_type is None or definition_type != "oauth2":
            raise ValueError("The security definition type is not recognised")

        if definition_flow is None or definition_flow not in self.v2_auth_flows:
            raise ValueError("The security definition flow is not recognised")
       
        if definition_flow == self.implict_flow:
            self.invoke_implicit_flow()

        if definition_flow == self.password_flow:
            self.invoke_password_flow()

        if definition_flow == self.application_flow:
            self.invoke_application_flow()

        if definition_flow == self.access_code_flow:
            auth_response = self.invoke_access_code_flow()
            self.create_connection(auth_response)

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

    def extract_paths(self):
        """ Return the paths only """
        return self.definition['paths']

    def extract_parameters(self):
        """ Return the parameters only """
        if self.definition.__contains__("parameters"):
            return self.definition['parameters']
        return None

    def extract_host(self):
        """ Return the host only """
        return self.definition['host']

    def extract_base_path(self):
        """ Return the base path only """
        return self.definition['basePath']
