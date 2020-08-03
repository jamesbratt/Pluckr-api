"""
Providers API
"""
import requests
import json
from tastypie.resources import ModelResource
from tastypie.authentication import ApiKeyAuthentication
from tastypie import fields

from api.resources import UserObjectsOnlyAuthorization, UserResource

from .models import Provider

class ProviderResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    """
    Provider API resource
    """
    class Meta:
        """ Resource meta """
        queryset = Provider.objects.all()
        resource_name = 'provider'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

    def alter_detail_data_to_serialize(self, request, data):
        swagger_url = data.obj.swagger_url
        response = requests.get(swagger_url)
        if response.status_code != 200:
            raise ValueError(response.json())

        swagger_definition = response.json()
        key = list(swagger_definition['securityDefinitions'])[0]
        data.data['swagger_definition'] = json.loads(json.dumps(swagger_definition['securityDefinitions'][key]))
        return data

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle
