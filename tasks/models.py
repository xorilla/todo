from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Project(models.Model):
    """Un projecte per agrupar tasques, sempre lligat a l'usuari que l'ha creat."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="usuari",
    )
    name = models.CharField("nom", max_length=100)
    created_at = models.DateTimeField("creat el", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="project_name_unique_per_user",
            )
        ]
        verbose_name = "projecte"
        verbose_name_plural = "projectes"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("tasks:project_list")


class Task(models.Model):
    """Una tasca per fer, sempre lligada a l'usuari que l'ha creada."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="usuari",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="projecte",
    )
    title = models.CharField("títol", max_length=200)
    notes = models.TextField("notes", blank=True)
    done = models.BooleanField("completada", default=False)
    created_at = models.DateTimeField("creada el", auto_now_add=True)
    updated_at = models.DateTimeField("actualitzada el", auto_now=True)
    due_date = models.DateField("data límit", blank=True, null=True)

    class Meta:
        ordering = ["done", "due_date", "-created_at"]
        verbose_name = "tasca"
        verbose_name_plural = "tasques"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("tasks:list")

    @property
    def is_overdue(self) -> bool:
        """La data límit ha passat i la tasca encara no està feta."""
        return bool(
            self.due_date and not self.done and self.due_date < timezone.localdate()
        )
