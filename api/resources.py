import re, json
from django.core import serializers
from django.core import exceptions
from django.contrib.auth.models import User
from django.conf.urls import url
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from tastypie.resources import ModelResource, Resource, ALL_WITH_RELATIONS
from tastypie.authorization import Authorization
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.http import HttpUnauthorized, HttpForbidden, HttpBadRequest
from tastypie.authentication import ApiKeyAuthentication
from tastypie.utils import trailing_slash
from .exceptions import CustomBadRequest
from .models import Chart, DataSource, DataSet, Operation, Workspace, IntegrationAuth, Profile, Dashboard
from .utils import clone_chart
from integrations.integrate import integrate, integrateRequest

class UserAccountAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        return object_list.filter(id=bundle.request.user.id)

    def read_detail(self, object_list, bundle):
        return bundle.obj.id == bundle.request.user.id

    def update_detail(self, object_list, bundle):
        return bundle.obj.id == bundle.request.user.id

    def delete_list(self, object_list, bundle):
        return bundle.obj.id == bundle.request.user.id

    def delete_detail(self, object_list, bundle):
        return bundle.obj.id == bundle.request.user.id

class UserObjectsOnlyAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        # This assumes a ``QuerySet`` from ``ModelResource``.
        return object_list.filter(user=bundle.request.user)

    def read_detail(self, object_list, bundle):
        # Is the requested object owned by the user?
        return bundle.obj.user == bundle.request.user

    def create_list(self, object_list, bundle):
        # Assuming they're auto-assigned to ``user``.
        return object_list

    def update_list(self, object_list, bundle):
        allowed = []

        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            if obj.user == bundle.request.user:
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

    def delete_list(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

    def delete_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        authentication = ApiKeyAuthentication()
        authorization = UserAccountAuthorization()

class IntegrationResource(ModelResource):
    class Meta:
        queryset = IntegrationAuth.objects.all()
        resource_name = 'integration_auth'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()

class WorkspaceResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    class Meta:
        queryset = Workspace.objects.all()
        resource_name = 'workspace'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle

class ChartResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    class Meta:
        queryset = Chart.objects.all()
        resource_name = 'chart'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle

class DashboardResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    charts = fields.ToManyField(ChartResource, 'chart', full=True, null=True, blank=True)
    class Meta:
        queryset = Dashboard.objects.all()
        resource_name = 'dashboard'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

    def save_m2m(self, bundle):
        return bundle

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle

class ChartLibraryResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    class Meta:
        queryset = Chart.objects.filter(is_published=True)
        resource_name = 'library'
        always_return_data = True
        authentication = ApiKeyAuthentication()

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/publish%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('publish'), name="publish"),
            url(r"^(?P<resource_name>%s)/install%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('install'), name="install"),
        ]

    def publish(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        chart_id = data.get('chart_id', '')

        try:
            clone_chart(chart_id, request, True, None)
        except ValueError as error:
            return self.create_response(request, {
                'success': False,
                'reason': error,
            }, HttpBadRequest )

        return self.create_response(request, {
            'success': True,
            'message': 'Your chart has been successfully published'
        })

    def install(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        chart_id = data.get('chart_id', '')
        tokens = data.get('tokens', '')

        try:
            cloned_chart = clone_chart(chart_id, request, False, tokens)
        except ValueError as error:
            raise CustomBadRequest(
                code="installation_error",
                message=str(error))

        cloned_chart_to_json = json.loads(serializers.serialize("json", [cloned_chart]))[0]['fields']
        cloned_chart_to_json['id'] = json.loads(serializers.serialize("json", [cloned_chart]))[0]['pk']
        return self.create_response(request, {
            'success': True,
            'chart': cloned_chart_to_json
        })

class DataSourceResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    chart = fields.ForeignKey(ChartResource, 'chart')
    integration_auth = fields.ForeignKey(IntegrationResource, 'integration_auth', null=True, blank=True)
    class Meta:
        queryset = DataSource.objects.all()
        resource_name = 'datasource'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()
        filtering = {
            'chart': ALL_WITH_RELATIONS,
        }

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        bundle.data['chart'] = bundle.obj.chart_id
        bundle.data['integration_auth'] = bundle.obj.integration_auth_id
        return bundle

class DataSetResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    chart = fields.ForeignKey(ChartResource, 'chart', full=True)
    sources = fields.ToManyField(DataSourceResource, 'sources', full=True)
    class Meta:
        queryset = DataSet.objects.all()
        resource_name = 'dataset'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()
        filtering = {
            'chart': ALL_WITH_RELATIONS,
        }

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle

class OperationResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    dataset = fields.ForeignKey(DataSetResource, 'dataset', full=True)
    class Meta:
        queryset = Operation.objects.all()
        resource_name = 'operation'
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()
        limit = 0
        max_limit = 0
        filtering = {
            'dataset': ALL_WITH_RELATIONS,
        }

    def hydrate(self, bundle):
        bundle.obj.user = bundle.request.user
        return bundle

    def dehydrate(self, bundle):
        del bundle.data['user']
        return bundle

class SignupResource(ModelResource):

    class Meta:
        queryset = User.objects.all()
        detail_allowed_methods = ['post']
        list_allowed_methods = ['post']
        always_return_data = True
        authentication = Authentication()
        authorization = Authorization()
        resource_name = 'signup'

    def dehydrate(self, bundle):
        bundle.data['key'] = bundle.obj.api_key.key
        del bundle.data['password']
        return bundle

    def obj_create(self, bundle, **kwargs):
        REQUIRED_USER_FIELDS = ("username", "raw_password", "contact")
        username = bundle.data["username"]

        if bundle.data["contact"] is False:
            raise CustomBadRequest(
                code="contact_confirmation",
                message="Please agree to be contacted by Pluckr."
            )

        for field in REQUIRED_USER_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a user."
                    .format(missing_key=field))
        try:
            email_regex = re.compile(r"^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$")

            if not email_regex.match(username):
                raise CustomBadRequest(
                    code="invalid_email",
                    message="The email address submitted is invalid.")

            if User.objects.filter(username=username):
                raise CustomBadRequest(
                    code="duplicate_exception",
                    message="That username is already taken.")
        except KeyError as missing_key:
            raise CustomBadRequest(
                code="missing_key",
                message="Must provide {missing_key} when creating a user."
                .format(missing_key=missing_key))
        except User.DoesNotExist:
            pass

        raw_password = bundle.data.pop('raw_password')

        try:
            validate_password(raw_password)
        except exceptions.ValidationError as error:
            raise CustomBadRequest(
                code="password_validation_error",
                message=str(error.messages[0]))

        bundle.obj = User.objects.create_user(username=username, password=raw_password)
        bundle.obj.save()

        Profile.objects.create(
            user=bundle.obj,
            can_be_contacted=True,
        )

        return bundle

class AuthenticationResource(Resource):

    def __get_api_key_for_user(self, user):
        return '%s' % (user.api_key.key)

    class Meta:
        resource_name = 'authentication'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/login%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('login'), name="api_login"),
        ]

    def login(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        username = data.get('username', '')
        password = data.get('password', '')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                return self.create_response(request, {
                    'api_key': self.__get_api_key_for_user(user),
                    'username': username,
                    'id': user.id
                    })
            else:
                return self.create_response(request, {
                    'success': False,
                    'reason': 'disabled',
                    }, HttpForbidden )
        else:
            return self.create_response(request, {
                'success': False,
                'reason': 'Incorrect user name or password',
                }, HttpUnauthorized )

class IntegrationAuthResource(Resource):

    class Meta:
        resource_name = 'integration-auth'
        authentication = ApiKeyAuthentication()

    def dispatch(self, request_type, request, **kwargs):
        self.is_authenticated(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        integration_type = data.get('integration_type', '')
        integration_payload = data.get('integration_payload', '')

        try:
            response = integrate(integration_type, integration_payload, request)
        except ValueError as error:
            raise CustomBadRequest(
                code="integration_authentication_error",
                message=str(error))

        return self.create_response(request, response)

class IntegrationRequestResource(Resource):

    class Meta:
        resource_name = 'integration-request'
        authentication = ApiKeyAuthentication()

    def dispatch(self, request_type, request, **kwargs):
        self.is_authenticated(request)
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        integration_url = data.get('url', None)
        integration_key = data.get('key', None)
        integration_type = data.get('integration_type', None)
        source_id = data.get('source_id', None)

        try:
            response = integrateRequest(integration_url, integration_key, integration_type, source_id)
        except ValueError as error:
            raise CustomBadRequest(
                code="integration_proxy_error",
                message=str(error))

        return self.create_response(request, response)
