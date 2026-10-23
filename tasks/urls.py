from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("nova/", views.task_create, name="create"),
    path("<int:pk>/editar/", views.task_edit, name="edit"),
    path("<int:pk>/toggle/", views.task_toggle, name="toggle"),
    path("<int:pk>/esborrar/", views.task_delete, name="delete"),
]
