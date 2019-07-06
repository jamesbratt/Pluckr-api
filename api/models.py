from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

class Chart(models.Model):
    name = models.CharField(max_length=100)
    chart_type = models.CharField(max_length=100)
    series_type = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

class DataSource(models.Model):
    name = models.CharField(max_length=100)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    provider = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)
    params = JSONField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

class DataSet(models.Model):
    name = models.CharField(max_length=100)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    y_axis_id = models.CharField(max_length=100, blank=True)
    data = JSONField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

class Operation(models.Model):
    name = models.CharField(max_length=100)
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE)
    root_function = models.CharField(max_length=100)
    ast = JSONField()
    sort_order = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class IntegrationAuth(models.Model):
    integration_type = models.CharField(max_length=100)
    access_token = models.TextField(blank=True) # Short/long-lived token
    refresh_token = models.TextField(blank=True)
    expiry = models.IntegerField(blank=True) # Seconds till expirt of access_token
    req_date = models.DateTimeField('date requested', blank=True) # The date and time that the access_token was requested
    user = models.ForeignKey(User, on_delete=models.CASCADE)

def signals_import():
    """ A note on signals.
    The signals need to be imported early on so that they get registered
    by the application. Putting the signals here makes sure of this since
    the models package gets imported on the application startup.
    Important note: added it as a function in case someone does a ctrl+shift+O
    in eclipse, the import will not be moved to the top of this file.
    """
    from tastypie.models import create_api_key

    models.signals.post_save.connect(create_api_key, sender=User)

signals_import()
