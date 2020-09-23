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
from tastypie.authorization import Authorization

from django.views.generic import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.db.models import Q

from api.resources import UserObjectsOnlyAuthorization, UserResource

from .models import Provider
from .utils import generate_url, Swagger, V2OpenApiSpecConnection, V3OpenApiSpecConnection, VERSION_2, VERSION_3

# TODO: Sub class this
class UserProvidersOnlyAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        return object_list.filter(Q(user=bundle.request.user) | Q(is_public=True))

    def read_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user or bundle.obj.is_public is True

    def create_list(self, object_list, bundle):
        return object_list

    def update_list(self, object_list, bundle):
        allowed = []

        for obj in object_list:
            if obj.user == bundle.request.user:
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

    def delete_list(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

    def delete_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

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

        return HttpResponseRedirect("http://localhost:3000" if settings.DEBUG else "https://app.pluckr.io")

class ProviderConnect(View):
    """ Redirect to an integrations authorization page """

    def get(self, request, **kwargs):
        """ Get the redirect url """
        provider = Provider.objects.get(pk=self.kwargs['pk'])
        scope_delimitter = provider.scope_delimitter if provider.scope_delimitter else ' '
        stringified_scopes = scope_delimitter.join(provider.scopes)
        scopes = stringified_scopes + ' ' + provider.scope_extensions if provider.scope_extensions else stringified_scopes
        params = [
            ('client_id', provider.client_id),
            ('redirect_uri', urllib.parse.quote(("http://localhost:8000" if settings.DEBUG else "https://api.pluckr.io") + '/providers/authenticate/' + str(provider.id) + '/')),
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

        if parameter_extensions:
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
        authorization = UserProvidersOnlyAuthorization()

    def check_is_valid_definition(self, swagger_url, security_scheme):
        Swagger(swagger_url, security_scheme)

    def obj_create(self, bundle, **kwargs):
        try:
            self.check_is_valid_definition(bundle.data["swagger_url"], None)
        except ValueError as error:
            raise ImmediateHttpResponse(HttpBadRequest(error))
        return super(ProviderResource, self).obj_create(bundle, **kwargs)

    def obj_update(self, bundle, **kwargs):
        try:
            self.check_is_valid_definition(bundle.data["swagger_url"], bundle.data["security_scheme"])
        except ValueError as error:
            raise ImmediateHttpResponse(HttpBadRequest(error))
        return super(ProviderResource, self).obj_update(bundle, **kwargs)

    def hydrate(self, bundle):
        if bundle.request.method == "POST":
            bundle.obj.user = bundle.request.user
        return bundle 

    def dehydrate(self, bundle):
        if bundle.obj.user != bundle.request.user:
            del bundle.data["client_id"]
            del bundle.data["scopes"]
            del bundle.data["api_base_url_override"]
            del bundle.data["parameter_extensions"]
            del bundle.data["scope_delimitter"]
            del bundle.data["scope_extensions"]
            
        del bundle.data["user"]

        bundle.data["client_secret"] = "SECRET_KEY" if bundle.data["client_secret"] else None
        bundle.data["api_key"] = "SECRET_KEY" if bundle.data["api_key"] else None
        try:
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

        except ValueError as error:
            raise ImmediateHttpResponse(HttpBadRequest(error))

        if bundle.obj.connection is not None or bundle.obj.api_key:
            bundle.data["isConnected"] = True
        else:
            bundle.data["isConnected"] = False

        bundle.data["isOwner"] = bundle.obj.user == bundle.request.user
        return bundle
