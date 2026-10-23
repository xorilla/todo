from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Task(models.Model):
    """Una tasca per fer, sempre lligada a l'usuari que l'ha creada."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="usuari",
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
