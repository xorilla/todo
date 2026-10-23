from django.contrib import admin
from django.urls import include, path

from tasks import views as task_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/registre/", task_views.register, name="register"),
    path("", include("tasks.urls")),
]
