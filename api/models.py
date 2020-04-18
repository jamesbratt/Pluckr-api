import requests, json
from requests.auth import HTTPBasicAuth
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    can_be_contacted = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Workspace(models.Model):
    title = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.title)

class IntegrationAuth(models.Model):
    integration_type = models.CharField(max_length=100)
    key = models.TextField(blank=True)
    access_token = models.TextField(blank=True) # Short/long-lived token
    refresh_token = models.TextField(blank=True)
    site_id = models.TextField(default=None, blank=True, null=True)
    host = models.TextField(null=True, blank=True)
    tenantId = models.TextField(null=True, blank=True)
    expiry = models.IntegerField(blank=True) # Seconds till expirt of access_token
    req_date = models.DateTimeField('date requested', blank=True) # The date and time that the access_token was requested
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)

class Chart(models.Model):
    name = models.CharField(max_length=100)
    chart_type = models.CharField(max_length=100)
    series_type = models.CharField(max_length=100)
    background_color = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    color_range = models.TextField(null=True, blank=True)
    x_axis_title = models.CharField(max_length=100, blank=True)
    y_axis_title = models.CharField(max_length=100, blank=True)
    x_axis_enabled = models.BooleanField(default=True, blank=True)
    is_published = models.BooleanField(default=False, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.name)

class Dashboard(models.Model):
    name = models.CharField(max_length=100)
    charts = models.ManyToManyField(Chart, through='DashboardMember', blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.name)

class DashboardMember(models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    order = models.IntegerField()

class DataSource(models.Model):
    name = models.CharField(max_length=100)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    provider = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)
    params = JSONField(blank=True, null=True)
    pages = models.IntegerField(blank=True, null=True, default=0)
    integration_auth = models.ForeignKey(IntegrationAuth, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.name)

class DataSet(models.Model):
    name = models.CharField(max_length=100)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    y_axis_enabled = models.BooleanField(default=False, blank=True)
    y_axis_is_opposite = models.BooleanField(default=False, blank=True)
    y_axis_title = models.CharField(max_length=100, blank=True)
    y_axis_id = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)
    sources = models.ManyToManyField(DataSource, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.name)

class Operation(models.Model):
    name = models.CharField(max_length=100)
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE)
    root_function = models.CharField(max_length=100)
    ast = JSONField()
    sort_order = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)

def add_to_mailing_list(sender, instance, **kwargs):
    if settings.DEBUG is False:
        api_key = settings.MAILCHIMP_API_KEY
        username = settings.MAILCHIMP_USERNAME
        list_id = settings.MAILCHIMP_LIST_ID
        headers = {'Content-Type': 'application/json'}
        try:
            requests.post(
                'https://us4.api.mailchimp.com/3.0/lists/' + list_id,
                headers=headers,
                data=json.dumps({'members': [{'email_address':instance.user.username, 'status':'subscribed'}]}),
                auth=HTTPBasicAuth(username, api_key)
            )
        except Exception:
            pass

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
    models.signals.post_save.connect(add_to_mailing_list, sender=Profile)

signals_import()
