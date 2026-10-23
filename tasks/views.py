from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task


def register(request):
    """Registre d'usuaris nous; a l'acabar queda la sessió iniciada."""
    if request.user.is_authenticated:
        return redirect("tasks:list")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Compte creat. Benvingut, comencem amb les tasques!")
            return redirect("tasks:list")
    else:
        form = UserCreationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)

    filt = request.GET.get("filtre", "")
    if filt == "pendents":
        tasks = tasks.filter(done=False)
    elif filt == "fetes":
        tasks = tasks.filter(done=True)

    return render(
        request,
        "tasks/task_list.html",
        {"tasks": tasks, "current_filter": filt},
    )


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, "Tasca creada.")
            return redirect("tasks:list")
    else:
        form = TaskForm()

    return render(request, "tasks/task_form.html", {"form": form, "editing": False})


def _get_own_task(request, pk: int) -> Task:
    """Carrega la tasca només si pertany a l'usuari actual (404 altrament)."""
    return get_object_or_404(Task, pk=pk, user=request.user)


@login_required
def task_edit(request, pk):
    task = _get_own_task(request, pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Tasca actualitzada.")
            return redirect("tasks:list")
    else:
        form = TaskForm(instance=task)

    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "task": task, "editing": True},
    )


@login_required
@require_POST
def task_toggle(request, pk):
    """Marca la tasca com a feta o com a pendent (només POST)."""
    task = _get_own_task(request, pk)
    task.done = not task.done
    task.save(update_fields=["done", "updated_at"])
    if task.done:
        messages.success(request, "Tasca completada. Bona feina!")
    else:
        messages.info(request, "Tasca tornada a posar com a pendent.")
    return redirect("tasks:list")


@login_required
def task_delete(request, pk):
    task = _get_own_task(request, pk)

    if request.method == "POST":
        task.delete()
        messages.success(request, "Tasca esborrada.")
        return redirect("tasks:list")

    return render(request, "tasks/task_confirm_delete.html", {"task": task})
