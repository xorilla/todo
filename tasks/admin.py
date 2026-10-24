from django.contrib import admin

from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    search_fields = ("name",)
    list_per_page = 50


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "project", "done", "due_date", "created_at")
    list_filter = ("done", "project")
    search_fields = ("title", "notes")
    list_per_page = 50
