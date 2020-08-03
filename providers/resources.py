"""
Providers API
"""
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

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle
