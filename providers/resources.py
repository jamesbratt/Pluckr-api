"""
Providers API
"""
import json
import urllib
from tastypie.resources import ModelResource
from tastypie.authentication import ApiKeyAuthentication
from tastypie import fields
from tastypie.http import HttpBadRequest
from tastypie.validation import Validation
from tastypie.exceptions import ImmediateHttpResponse

from django.views.generic import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect

from api.resources import UserObjectsOnlyAuthorization, UserResource

from .models import Provider
from .utils import generate_url, Swagger, V2OpenApiSpecConnection, V3OpenApiSpecConnection, VERSION_2, VERSION_3

class ProviderAuthenticate(View):
    """ Authenticate with the provider """

    def get(self, request, **kwargs):
        """ GET """
        provider = get_object_or_404(Provider, pk=self.kwargs['pk'])

        try:
            swagger_url = provider.swagger_url
            security_scheme = provider.security_scheme
            swagger = Swagger(swagger_url, security_scheme)
            swagger_version = swagger.version
            security_definition = swagger.extract_security_definition()

            if swagger_version == VERSION_2:
                V2OpenApiSpecConnection(
                    request,
                    security_definition,
                    provider
                ).invoke_auth_flow()

            if swagger_version == VERSION_3:
                V3OpenApiSpecConnection(
                    request,
                    security_definition,
                    provider
                ).invoke_auth_flow()

        except ValueError as err:
            resp = err.args[0]
            status_code = 400
            response = HttpResponse(json.dumps(resp))
            response.status_code = status_code
            return response

        return HttpResponseRedirect("http://localhost:3000")

class ProviderConnect(View):
    """ Redirect to an integrations authorization page """

    def get(self, request, **kwargs):
        """ Get the redirect url """
        provider = Provider.objects.get(pk=self.kwargs['pk'])
        stringified_scopes = ','.join(provider.scopes)
        scopes = stringified_scopes + ',' + provider.scope_extensions if provider.scope_extensions is not None else stringified_scopes
        params = [
            ('client_id', provider.client_id),
            ('redirect_uri', urllib.parse.quote('http://localhost:8000/providers/authenticate/' + str(provider.id) + '/')),
            ('response_type', 'code'),
            ('scope', urllib.parse.quote(scopes))
        ]

        try:
            swagger_url = provider.swagger_url
            security_scheme = provider.security_scheme
            security_definition = Swagger(swagger_url, security_scheme).extract_security_definition()
        except ValueError as err:
            resp = err.args[0]
            status_code = 400
            response = HttpResponse(json.dumps(resp))
            response.status_code = status_code
            return response

        endpoint = security_definition['authorizationUrl']
        parameter_extensions = provider.parameter_extensions

        if parameter_extensions is not None:
            parameter_extensions_dict = json.loads(parameter_extensions)
            for key in parameter_extensions_dict:
                params.append((key, parameter_extensions_dict[key]))

        url = generate_url(endpoint, params)
        return HttpResponseRedirect(url)

class ProviderResource(ModelResource):
    """
    Provider API resource
    """
    user = fields.ForeignKey(UserResource, 'user')
    class Meta:
        """ Resource meta """
        queryset = Provider.objects.all()
        resource_name = 'provider'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

    def check_is_valid_definition(self, swagger_url):
        Swagger(swagger_url)

    def obj_create(self, bundle, **kwargs):
        try:
            self.check_is_valid_definition(bundle.data["swagger_url"])
        except ValueError:
            raise ImmediateHttpResponse(HttpBadRequest("Invalid Swagger Definition"))
        return super(ProviderResource, self).obj_create(bundle, **kwargs)

    def obj_update(self, bundle, **kwargs):
        try:
            self.check_is_valid_definition(bundle.data["swagger_url"])
        except ValueError:
            raise ImmediateHttpResponse(HttpBadRequest("Invalid Swagger Definition"))
        return super(ProviderResource, self).obj_update(bundle, **kwargs)

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data["user"]

        swagger_url = bundle.data["swagger_url"]
        security_scheme = bundle.data["security_scheme"]

        swagger_instance = Swagger(swagger_url, security_scheme)

        bundle.data["security_options"] = json.loads(
            json.dumps(
                swagger_instance.extract_security_options()
            )
        )

        bundle.data["swagger_definition"] = json.loads(
            json.dumps(
                swagger_instance.extract_security_definition()
            )
        )

        bundle.data["swagger_paths"] = json.loads(
            json.dumps(
                swagger_instance.extract_paths()
            )
        )

        bundle.data["swagger_parameters"] = json.loads(
            json.dumps(
                swagger_instance.extract_parameters()
            )
        )

        bundle.data["swagger_host"] = swagger_instance.extract_host()

        bundle.data["swagger_base_path"] = swagger_instance.extract_base_path()

        if bundle.obj.connection is not None:
            bundle.data["isConnected"] = True
        else:
            bundle.data["isConnected"] = False
        return bundle
