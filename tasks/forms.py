from django import forms

from .models import Project, Task


class TaskForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        """Limita els projectes disponibles als de l'usuari actual."""
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["project"].queryset = Project.objects.filter(user=user)
        self.fields["project"].empty_label = "Sense projecte"

    class Meta:
        model = Task
        fields = ["title", "notes", "due_date", "project"]
        widgets = {
            "title": forms.TextInput(
                attrs={"autofocus": True, "placeholder": "p. ex. Comprar llet"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class ProjectForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        """Recorda l'usuari per validar que no repeteixi nom de projecte."""
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if self.user is not None:
            existing = Project.objects.filter(user=self.user, name=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(
                    "Ja tens un projecte amb aquest nom."
                )
        return name

    class Meta:
        model = Project
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "autofocus": True,
                    "placeholder": "p. ex. Web de la botiga",
                }
            ),
        }
