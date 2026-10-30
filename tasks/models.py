from django.conf import settings
from django.core.exceptions import ValidationError
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

    class Status(models.TextChoices):
        PENDING = "pending", "pendent"
        IN_PROGRESS = "in_progress", "en procés"
        DONE = "done", "completada"

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
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subtasks",
        verbose_name="tasca pare",
    )
    title = models.CharField("títol", max_length=200)
    notes = models.TextField("notes", blank=True)
    status = models.CharField(
        "estat",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField("creada el", auto_now_add=True)
    updated_at = models.DateTimeField("actualitzada el", auto_now=True)
    due_date = models.DateField("data límit", blank=True, null=True)

    class Meta:
        # Les pendents i les en procés es barregen, ordenades per data;
        # les completades queden sempre al final.
        ordering = [
            models.Case(
                models.When(status="done", then=models.Value(1)),
                default=models.Value(0),
                output_field=models.IntegerField(),
            ),
            "due_date",
            "-created_at",
        ]
        verbose_name = "tasca"
        verbose_name_plural = "tasques"

    def __str__(self) -> str:
        return self.title

    def clean(self):
        """Un sol nivell de jerarquia: les subtasques no en poden tenir."""
        super().clean()
        if self.parent_id:
            parent = self.parent
            if parent.parent_id is not None:
                raise ValidationError(
                    {"parent": "Una subtasca no pot tenir subtasques."}
                )
            if self.user_id and parent.user_id != self.user_id:
                raise ValidationError(
                    {"parent": "La tasca pare ha de ser teva."}
                )

    def get_absolute_url(self) -> str:
        return reverse("tasks:list")

    @property
    def done(self) -> bool:
        """Legacy: la tasca està finalitzada (abans un camp booleà)."""
        return self.status == self.Status.DONE

    @property
    def in_progress(self) -> bool:
        return self.status == self.Status.IN_PROGRESS

    def advance_state(self) -> "Task.Status":
        """Segueix el cicle pendent → en procés → completada → pendent."""
        next_status = {
            self.Status.PENDING: self.Status.IN_PROGRESS,
            self.Status.IN_PROGRESS: self.Status.DONE,
            self.Status.DONE: self.Status.PENDING,
        }.get(self.status, self.Status.PENDING)
        self.status = next_status
        return next_status

    @property
    def is_overdue(self) -> bool:
        """La data límit ha passat i la tasca encara no està feta."""
        return bool(
            self.due_date
            and self.status != self.Status.DONE
            and self.due_date < timezone.localdate()
        )

    @property
    def subtask_counts(self) -> "tuple[int, int]":
        """(completades, totals) entre les subtasques pròpies.

        Fa servir la caché del prefetch_related quan hi ha; no toca la BD.
        """
        subs = list(self.subtasks.all())
        done = sum(1 for s in subs if s.status == self.Status.DONE)
        return done, len(subs)
