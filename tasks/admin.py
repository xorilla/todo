from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "done", "due_date", "created_at")
    list_filter = ("done",)
    search_fields = ("title", "notes")
    list_per_page = 50
