from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "notes", "due_date"]
        widgets = {
            "title": forms.TextInput(
                attrs={"autofocus": True, "placeholder": "p. ex. Comprar llet"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
