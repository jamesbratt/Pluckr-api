from django.contrib.auth.models import User
from django.conf.urls import url
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from tastypie.resources import ModelResource, Resource
from tastypie.authorization import Authorization
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.http import HttpUnauthorized, HttpForbidden
from tastypie.authentication import ApiKeyAuthentication
from tastypie.utils import trailing_slash
from .exceptions import CustomBadRequest
from .models import Chart, DataSource, DataSet, Operation

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
        authorization = Authorization()


class ChartResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    class Meta:
        queryset = Chart.objects.all()
        resource_name = 'chart'
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

class DataSourceResource(ModelResource):
    chart = fields.ForeignKey(ChartResource, 'chart')
    class Meta:
        queryset = DataSource.objects.all()
        resource_name = 'datasource'
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

class DataSetResource(ModelResource):
    chart = fields.ForeignKey(ChartResource, 'chart')
    data_source = fields.ForeignKey(DataSourceResource, 'data_source')
    class Meta:
        queryset = DataSet.objects.all()
        resource_name = 'dataset'
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

class OperationResource(ModelResource):
    dataset = fields.ForeignKey(DataSetResource, 'dataset')
    class Meta:
        queryset = Operation.objects.all()
        resource_name = 'operation'
        authentication = ApiKeyAuthentication()
        authorization = UserObjectsOnlyAuthorization()

class SignupResource(ModelResource):

    class Meta:
        queryset = User.objects.all()
        detail_allowed_methods = ['post']
        list_allowed_methods = ['post']
        always_return_data = True
        authentication = Authentication()
        authorization = Authorization()
        resource_name = 'signup'
        # fields = ['email', 'first_name', 'last_name', 'phone_number', 'username']

    def dehydrate(self, bundle):
        bundle.data['key'] = bundle.obj.api_key.key
        del bundle.data['password']
        return bundle

    def obj_create(self, bundle, **kwargs):
        REQUIRED_USER_FIELDS = ("username", "email", "first_name", "last_name", "raw_password")
        for field in REQUIRED_USER_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a user."
                    .format(missing_key=field))
        try:
            username = bundle.data["username"]
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
        bundle.data["password"] = make_password(raw_password)
        return super(SignupResource, self).obj_create(bundle, **kwargs)

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
                    'username': username
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

