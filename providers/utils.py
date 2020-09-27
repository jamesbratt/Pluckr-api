""" Generic utilities for providers """

import time
from datetime import timezone
import datetime
import requests
from cryptography.fernet import Fernet

from django.conf import settings
from api.models import IntegrationAuth
from .models import Provider

def generate_url(endpoint, params):
    """ Building the oauth authorisation url """
    url = endpoint
    for i, (param_key, param) in enumerate(params):
        symbol = '&'
        if i == 0 and '?' not in url:
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
        if connection.expiry != 0:
            expiry_date = connection.req_date + datetime.timedelta(seconds=connection.expiry)
            if expiry_date < datetime.datetime.now(timezone.utc):
                return True
            return False
        return False

    def get_token(self):
        """ Get the appropriate token based on the provider """

        connection = self.provider.connection

        if connection is None:
            raise ValueError("A connection has not been established with " + self.provider.name)

        if self.should_refresh(connection):
            connection = Connection(
                self.request,
                self.security_definition,
                self.provider
            ).update_oauth_access_token()

        return connection.access_token

    def proxy_api_key_request(self, retry=True):
        headers = {'Content-Type': 'application/json'}

        url = self.uri
        name = self.security_definition["name"]
        token = self.provider.api_key

        if self.security_definition["in"] == "header":
            headers[name] = token

        if self.security_definition["in"] == "query":
            url = generate_url(self.uri, [(name, token)])

        if self.security_definition["in"] == "cookie":
            raise ValueError("API keys passed in a cookie is not yet supported")

        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            raise ValueError(response.reason + ": " + response.text if response.text else "Unknown resource")
        if response.status_code != 200:
            if retry is True:
                time.sleep(2)
                return self.proxy_api_key_request(False)
            raise ValueError(response.json())
        return response.json()

    def proxy_oauth2_request(self, retry=True):
        token = self.get_token()
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
        response = requests.get(self.uri, headers=headers)
        if response.status_code == 404:
            raise ValueError(response.reason + ": " + response.text if response.text else "Unknown resource")
        if response.status_code != 200:
            if retry is True:
                time.sleep(2)
                return self.proxy_oauth2_request(False)
            raise ValueError(response.json())
        return response.json()

    def proxy_request(self):
        """ Make the http request """

        auth_type = self.security_definition["type"]

        if auth_type == "oauth2":
            return self.proxy_oauth2_request()

        if auth_type == "apiKey":
            return self.proxy_api_key_request()

        raise ValueError(auth_type + " is an unsupported authentication mechanism.")

class Connection:
    """ Establishing a connection with a provider """

    def __init__(self, request, security_definition, provider):
        self.request = request
        self.security_definition = security_definition
        self.provider = provider

    def create_connection(self, auth_response):
        """ Create an integration object and link it to the provider """

        expires_in = auth_response['expires_in'] if 'expires_in' in auth_response else 0
        req_date = datetime.datetime.now(timezone.utc)
        auth_key = Fernet.generate_key()
        integration_creds = IntegrationAuth(
            integration_type=self.provider.name,
            key=auth_key.decode("utf-8"),
            access_token=auth_response['access_token'],
            expiry=expires_in,
            req_date=req_date,
            user=self.provider.user,
        )
        if 'refresh_token' in auth_response:
            integration_creds.refresh_token = auth_response['refresh_token']

        integration_creds.save()
        self.provider.connection = integration_creds
        self.provider.save()

    def fetch_oauth_token(self, token_url, code):
        """ Making an http request for an oauth token """

        payload = {
            'client_id': self.provider.client_id,
            'client_secret': self.provider.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': ("http://localhost:8000" if settings.DEBUG else "https://api.pluckr.io") + '/providers/authenticate/' + str(self.provider.id) + '/'
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

        # Now update the connection entity with the new access token
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

class V3OpenApiSpecConnection(Connection):
    """ Connecting to an api with a v2 defintion """

    implict_flow = "implicit"
    password_flow = "password"
    client_credentials_flow = "clientCredentials"
    auth_code_flow = "authorizationCode"

    v3_auth_flows = [implict_flow, password_flow, client_credentials_flow, auth_code_flow]

    def invoke_auth_flow(self):
        """ Determine how to handle the connection """

        definition_type = self.security_definition["type"]
        definition_flow = self.security_definition["flow"]

        if definition_type is None or definition_type != "oauth2":
            raise ValueError("The security definition type is not recognised")

        if definition_flow is None or definition_flow not in self.v3_auth_flows:
            raise ValueError("The security definition flow is not recognised")

        if definition_flow == self.implict_flow:
            self.invoke_implicit_flow()

        if definition_flow == self.password_flow:
            self.invoke_password_flow()

        if definition_flow == self.client_credentials_flow:
            self.invoke_application_flow()

        if definition_flow == self.auth_code_flow:
            auth_response = self.invoke_access_code_flow()
            self.create_connection(auth_response)

VERSION_2 = "VERSION_2"
VERSION_3 = "VERSION_3"

SUPPORTED_V2_AUTH_METHODS = ["apiKey", "oauth2"]
SUPPORTED_V3_AUTH_METHODS = ["apiKey", "oauth2"]

class Swagger:
    """ Interacting with Swagger """

    def __init__(self, swagger_url, security_scheme=None):
        self.swagger_url = swagger_url
        self.security_scheme = security_scheme
        self.definition = self.fetch_definition()
        self.version = self.set_version()

        self.extract_security_definition()

    def set_version(self):

        if 'paths' not in self.definition:
            raise ValueError('There are no paths defined in your definition')
        if 'info' not in self.definition:
            raise ValueError('There is no info defined in your definition')

        if "swagger" in self.definition:
            if 'securityDefinitions' not in self.definition:
                raise ValueError('There are no security definitions defined in your definition')
            if 'basePath' not in self.definition:
                raise ValueError('There is no base path defined in your definition')
            if 'schemes' not in self.definition:
                raise ValueError('There are no schemes defined in your definition')

            return VERSION_2

        if "openapi" in self.definition:
            if 'components' not in self.definition:
                raise ValueError('There are no components defined in your definition')
            if 'servers' not in self.definition:
                raise ValueError('There are no servers defined in your definition')

            return VERSION_3

    def fetch_definition(self):
        """ Making an HTTP request for a swagger definition """
        response = requests.get(self.swagger_url)
        if response.status_code == 404:
            raise ValueError("The openAPI definition provided could not be found")
        if response.status_code != 200:
            raise ValueError(response.json())

        return response.json()

    def extract_security_definition(self):
        """ Return the security defintion only """

        if self.version == VERSION_2:
            key = self.security_scheme if self.security_scheme is not None else list(self.definition['securityDefinitions'])[0]
            scheme = self.definition['securityDefinitions'][key]
            if scheme['type'] not in SUPPORTED_V2_AUTH_METHODS:
                raise ValueError(scheme['type'] + " is not currently a supported authentication method.")

            return scheme

        if self.version == VERSION_3:
            if "securitySchemes" not in self.definition['components']:
                raise ValueError("There are no security schemes in your definition.")

            key = self.security_scheme if self.security_scheme is not None else list(self.definition['components']['securitySchemes'])[0]
            scheme = self.definition['components']['securitySchemes'][key]

            if scheme['type'] not in SUPPORTED_V3_AUTH_METHODS:
                raise ValueError(scheme['type'] + " is not currently a supported authentication method.")

            if "flows" in scheme:
                flow_schemes = list(scheme['flows'])
                scheme_key = next((x for x in flow_schemes if x == 'authorizationCode'), None)

                if scheme_key is None:
                    raise ValueError("The only supported oauth2 flow is: authorizationCode")

                scheme['flow'] = scheme_key
                scheme_root = scheme
                nested_flow_scheme = scheme['flows'][scheme_key]
                merged = {**scheme_root, **nested_flow_scheme}
                del merged['flows']
                return merged
            else:
                return scheme

    def extract_paths(self):
        """ Return the paths only """
        return self.definition['paths']

    def extract_security_options(self):
        """ Return the available security options """
        if self.version == VERSION_2:
            return list(self.definition['securityDefinitions'])

        if self.version == VERSION_3:
            return list(self.definition['components']['securitySchemes'])

    def extract_info(self):
        """ Return the paths only """
        return self.definition['info']

    def extract_parameters(self):
        """ Return the parameters only """
        if self.version == VERSION_2:
            if self.definition.__contains__("parameters"):
                return self.definition['parameters']
            return None

        if self.version == VERSION_3:
            if self.definition['components'].__contains__("parameters"):
                return self.definition['components']['parameters']
            return None

    def extract_host(self):
        """ Return the host only """
        if self.version == VERSION_2:
            return self.definition['schemes'][0] + '://' + self.definition['host']

        if self.version == VERSION_3:
            return self.definition['servers'][0]['url']

    def extract_base_path(self):
        """ Return the base path only """
        if self.version == VERSION_2:
            return self.definition['basePath']
        return None
