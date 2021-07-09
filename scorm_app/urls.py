from django.conf.urls import url

from .views import SyncXBlockData


urlpatterns = [
    url(
        r'^set_values$', SyncXBlockData.as_view(), name='set_values'
    ),
]
