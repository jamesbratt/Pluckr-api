
from django.conf.urls import url
from api.views import (
    api,
)

app_name = 'project'
urlpatterns = [
    url(r'^$', api.as_view()),
]