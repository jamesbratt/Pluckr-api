"""
Data Provider
"""
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from api.models import IntegrationAuth, Workspace

class Provider(models.Model):
    """
    Data Provider Model
    """
    name = models.CharField(max_length=100)
    swagger_url = models.TextField(blank=True, null=True)
    security_scheme = models.CharField(max_length=100, blank=True, null=True, default=None)
    client_id = models.TextField(blank=True, null=True)
    client_secret = models.TextField(blank=True, null=True)
    scopes = JSONField(blank=True, null=True, default=None)
    username = models.CharField(blank=True, null=True, max_length=100)
    api_key = models.TextField(blank=True, null=True)
    connection = models.OneToOneField(
        IntegrationAuth, blank=True, null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)
