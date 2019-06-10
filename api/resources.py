from tastypie.resources import ModelResource, Resource
from tastypie.authorization import Authorization
from tastypie import fields
from django.conf.urls import url
from google.oauth2 import id_token
from google.auth.transport import requests
from .models import Chart, DataSource, DataSet, Operation, Profile
from tastypie.authentication import Authentication

class GoogleAuthentication(Authentication):

    def is_authenticated(self, request, **kwargs):
        if 'Authorization' in request.headers:
            try:
                idinfo = id_token.verify_oauth2_token(
                    request.headers['Authorization'], requests.Request(),
                    '689997766659-hobsdn1iaid1sdc4r4v3pq494nsq8bn7.apps.googleusercontent.com'
                )

                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Wrong issuer.')

                return True

            except ValueError:
                pass

        return False

class ChartResource(ModelResource):
    class Meta:
        queryset = Chart.objects.all()
        resource_name = 'chart'
        authentication = GoogleAuthentication()
        authorization = Authorization()

class DataSourceResource(ModelResource):
    chart = fields.ForeignKey(ChartResource, 'chart')
    class Meta:
        queryset = DataSource.objects.all()
        resource_name = 'datasource'
        authentication = GoogleAuthentication()
        authorization = Authorization()

class DataSetResource(ModelResource):
    chart = fields.ForeignKey(ChartResource, 'chart')
    data_source = fields.ForeignKey(DataSourceResource, 'data_source')
    class Meta:
        queryset = DataSet.objects.all()
        resource_name = 'dataset'
        authentication = GoogleAuthentication()
        authorization = Authorization()

class OperationResource(ModelResource):
    dataset = fields.ForeignKey(DataSetResource, 'dataset')
    class Meta:
        queryset = Operation.objects.all()
        resource_name = 'operation'
        authentication = GoogleAuthentication()
        authorization = Authorization()

