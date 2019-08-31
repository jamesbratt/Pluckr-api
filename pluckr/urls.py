"""pluckr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# urls.py
from django.conf.urls import url, include
from tastypie.api import Api
from api.resources import ChartResource, ChartLibraryResource, DataSourceResource, DataSetResource, OperationResource, AuthenticationResource, SignupResource, IntegrationAuthResource, IntegrationRequestResource

v1_api = Api(api_name='v1')
v1_api.register(ChartResource())
v1_api.register(DataSourceResource())
v1_api.register(DataSetResource())
v1_api.register(OperationResource())
v1_api.register(AuthenticationResource())
v1_api.register(SignupResource())
v1_api.register(IntegrationAuthResource())
v1_api.register(IntegrationRequestResource())
v1_api.register(ChartLibraryResource())

urlpatterns = [
    url(r'^api/', include(v1_api.urls)),
]
