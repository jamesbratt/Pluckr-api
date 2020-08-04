from django.conf.urls import url
from providers.resources import (
    OauthLoginRedirect,
)

app_name = 'providers'
urlpatterns = [
    url(r'^connect/(?P<pk>[-\w]+)/$', OauthLoginRedirect.as_view(), name='oauth-login'),
]