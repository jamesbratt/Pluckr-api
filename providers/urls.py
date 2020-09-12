from django.conf.urls import url
from providers.resources import (
    ProviderConnect, ProviderAuthenticate
)

app_name = 'providers'
urlpatterns = [
    url(r'^connect/(?P<pk>[-\w]+)/$', ProviderConnect.as_view(), name='connect'),
    url(r'^authenticate/(?P<pk>[-\w]+)/$', ProviderAuthenticate.as_view(), name='authenticate'),
]