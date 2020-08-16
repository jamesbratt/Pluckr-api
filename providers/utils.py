""" Generic utilities for providers """

from datetime import timezone
import datetime
import requests
from cryptography.fernet import Fernet

from api.models import IntegrationAuth
from .models import Provider

def generate_url(endpoint, params):
    """ Building the oauth authorisation url """
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i == 0:
            symbol = '?'
        url += str(symbol + param_key + '=' + param)
    return url

class ProxyRequest:
    """ Proxying requests faciliated by connected providers """

    def __init__(self, request, uri, provider_id, source_id, security_definition):
        self.request = request
        self.uri = uri
        self.provider_id = provider_id
        self.source_id = source_id
        self.security_definition = security_definition

        try:
            self.provider = Provider.objects.get(pk=self.provider_id)
        except Provider.DoesNotExist:
            raise ValueError("A provider could not be found with the ID " + self.provider_id)

    def should_refresh(self, connection):
        """ Determine whether to use the refresh token """

        expiry_date = connection.req_date + datetime.timedelta(seconds=connection.expiry)
        if expiry_date < datetime.datetime.now(timezone.utc):
            return True
        return False

    def get_token(self):
        """ Get the appropriate token based on the provider """

        connection = self.provider.connection
        definition_type = self.security_definition["type"]

        if connection is None and definition_type != "oauth2":
            raise ValueError("Authentication mechanisms other than oauth2 are not yet fully supported")

        if connection is None:
            raise ValueError("A connection has not been established with " + self.provider.name)

        if self.should_refresh(connection):
            connection = Connection(
                self.request,
                self.security_definition,
                self.provider
            ).update_oauth_access_token()
        
        return connection.access_token

    def proxy_request(self):
        """ Make the http request """

        token = self.get_token()

        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
        response = requests.get("https://" + self.uri, headers=headers)
        if response.status_code != 200:
            raise ValueError(response.json())
        return response.json()

class Connection:
    """ Establishing a connection with a provider """

    def __init__(self, request, security_definition, provider):
        self.request = request
        self.security_definition = security_definition
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

    def update_oauth_access_token(self):
        """ Making an http request for an oauth refresh token """

        token_url = self.security_definition["tokenUrl"]
        connection = self.provider.connection

        payload = {
            'client_id': self.provider.client_id,
            'client_secret': self.provider.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': connection.refresh_token
        }

        response = requests.post(token_url, data=payload, headers={"Accept":"application/json"})
        if response.status_code != 200:
            raise ValueError(response.json())

        refresh_token_response = response.json()

        """ Now update the connection entity with the new access token """
        
        new_req_date = datetime.datetime.now(timezone.utc)
        connection.access_token = refresh_token_response['access_token']
        connection.req_date = new_req_date
        connection.save()
        return connection

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
