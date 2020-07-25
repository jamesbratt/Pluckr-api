"""
Providers API
"""
from tastypie.resources import ModelResource
from tastypie.authentication import ApiKeyAuthentication

from api.resources import UserObjectsOnlyAuthorization

from .models import Provider

class ProviderResource(ModelResource):
    """
    Provider API resource
    """
    class Meta:
        """ Resource meta """
        queryset = Provider.objects.all()
        resource_name = 'provider'
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()
