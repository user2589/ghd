from django.conf.urls import url

import views

urlpatterns = (
    url(r'^$', views.queue_repos),
    url(r'^([a-zA-Z0-9_-]{1,40})$', views.queue_user),
)
