import requests
import datetime
from datetime import timezone
from cryptography.fernet import Fernet
from integrations.github import github_authentication, github_proxy_request
from integrations.jira import jira_authentication, jira_proxy_request
from integrations.facebook import facebook_authentication, facebook_proxy_request
from integrations.salesforce import salesforce_authentication, salesforce_proxy_request
from integrations.stripe import stripe_authentication, stripe_proxy_request
from integrations.finance import finance_proxy_request
from integrations.wrike import wrike_authentication, wrike_proxy_request
from integrations.xero import xero_authentication, xero_proxy_request
from api.models import IntegrationAuth

def integrate(integration_type, payload, request):
    if integration_type == 'github':
        auth_response = github_authentication(payload)
        if auth_response:
            req_date = datetime.datetime.now(timezone.utc)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                expiry=0,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

    if integration_type == 'jira':
        auth_response = jira_authentication(payload)
        if auth_response:
            req_date = datetime.datetime.now(timezone.utc)
            expires_in = auth_response['expires_in']
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                refresh_token=auth_response['refresh_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

    if integration_type == 'facebook':
        auth_response = facebook_authentication(payload)
        if auth_response:
            expires_in = auth_response['expires_in']
            req_date = datetime.datetime.now(timezone.utc)
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

    if integration_type == 'salesforce':
        auth_response = salesforce_authentication(payload)
        if auth_response:
            expires_in = 7200
            req_date = datetime.datetime.now(timezone.utc)
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                refresh_token=auth_response['refresh_token'],
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

    if integration_type == 'stripe':
        auth_response = stripe_authentication(payload)
        if auth_response:
            expires_in = 0
            req_date = datetime.datetime.now(timezone.utc)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                refresh_token=auth_response['refresh_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

    if integration_type == 'wrike':
        auth_response = wrike_authentication(payload)
        if auth_response:
            expires_in = auth_response['expires_in']
            req_date = datetime.datetime.now(timezone.utc)
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                refresh_token=auth_response['refresh_token'],
                key=auth_key.decode("utf-8"),
                access_token=auth_response['access_token'],
                expiry=expires_in,
                req_date=req_date,
                host=auth_response['host'],
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

    if integration_type == 'xero':
        auth_response = xero_authentication(payload)
        if auth_response:
            expires_in = auth_response['expires_in']
            req_date = datetime.datetime.now(timezone.utc)
            expiry_date = req_date + datetime.timedelta(seconds=expires_in)
            auth_key = Fernet.generate_key()
            integration_creds = IntegrationAuth(
                integration_type=integration_type,
                refresh_token=auth_response['refresh_token'],
                key=auth_key.decode("utf-8"),
                tenantId=auth_response['tenantId'],
                access_token=auth_response['access_token'],
                expiry=expires_in,
                req_date=req_date,
                user=request.user,
            )
            integration_creds.save()

            return {'id': integration_creds.pk, 'key': auth_key, 'provider': integration_type}

def integrateRequest(url, key, integration_type, source_id):
    if integration_type == 'github':
        return github_proxy_request(url, key, source_id)

    if integration_type == 'facebook':
        return facebook_proxy_request(url, key, source_id)

    if integration_type == 'salesforce':
        return salesforce_proxy_request(url, key, source_id)

    if integration_type == 'jira':
        return jira_proxy_request(url, key, source_id)

    if integration_type == 'stripe':
        return stripe_proxy_request(url, key, source_id)

    if integration_type == 'wrike':
        return wrike_proxy_request(url, key, source_id)

    if integration_type == 'xero':
        return xero_proxy_request(url, key, source_id)

    if integration_type == 'finance':
        return finance_proxy_request(url)
