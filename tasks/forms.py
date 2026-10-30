from django import forms

from .models import Project, Task


class TaskForm(forms.ModelForm):
    def __init__(self, *args, user=None, parent=None, **kwargs):
        """Limita els projectes disponibles als de l'usuari actual.

        Si es crea com a subtasca (parent), el projecte s'hereta del pare
        i no es pot triar: el camp s'elimina del formulari.
        """
        super().__init__(*args, **kwargs)
        self.parent = parent
        if user is not None:
            self.fields["project"].queryset = Project.objects.filter(user=user)
        self.fields["project"].empty_label = "Sense projecte"
        # Les subtasques no trien projecte (l'hereten del pare), ni al crear
        # ni a l'editar.
        if self.parent is not None or self.instance.parent_id:
            self.fields.pop("project")

    class Meta:
        model = Task
        fields = ["title", "notes", "due_date", "project"]
        widgets = {
            "title": forms.TextInput(
                attrs={"autofocus": True, "placeholder": "p. ex. Comprar llet"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(
                attrs={"type": "date"},
                # <input type="date"> només admet el format ISO; amb la
                # localització en català es renderitzaria "d/m/A" i el
                # navegador ignoraria el valor (la data es perdria a l'editar).
                format="%Y-%m-%d",
            ),
        }

    def save(self, commit: bool = True) -> Task:
        task = super().save(commit=False)
        if self.parent is not None:
            task.parent = self.parent
            task.user = self.parent.user
            # Les subtasques hereden sempre el projecte de la pare.
            task.project = self.parent.project
        if commit:
            task.save()
        return task


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
