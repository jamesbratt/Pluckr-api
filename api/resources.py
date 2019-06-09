from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie import fields
from .models import Chart, DataSource, DataSet

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