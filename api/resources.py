from tastypie.resources import ModelResource, Resource
from tastypie.authorization import Authorization
from tastypie import fields
from django.conf.urls import url
from .models import Chart, DataSource, DataSet, Operation, Profile

class ChartResource(ModelResource):
    class Meta:
        queryset = Chart.objects.all()
        resource_name = 'chart'
        authorization = Authorization()

class DataSourceResource(ModelResource):
    chart = fields.ForeignKey(ChartResource, 'chart')
    class Meta:
        queryset = DataSource.objects.all()
        resource_name = 'datasource'
        authorization = Authorization()

class DataSetResource(ModelResource):
    chart = fields.ForeignKey(ChartResource, 'chart')
    data_source = fields.ForeignKey(DataSourceResource, 'data_source')
    class Meta:
        queryset = DataSet.objects.all()
        resource_name = 'dataset'
        authorization = Authorization()

class OperationResource(ModelResource):
    dataset = fields.ForeignKey(DataSetResource, 'dataset')
    class Meta:
        queryset = Operation.objects.all()
        resource_name = 'operation'
        authorization = Authorization()

