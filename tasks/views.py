from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ProjectForm, TaskForm
from .models import Project, Task


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


def _list_url(request) -> str:
    """URL de la llista amb els filtres de la petició actual (si n'hi ha)."""
    url = reverse("tasks:list")
    query = request.GET.urlencode()
    return f"{url}?{query}" if query else url


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)

    # Sense paràmetre es mostren les pendents ("totes" per veure-les totes).
    filt = request.GET.get("filtre", "")
    if filt == "totes":
        filt = "totes"
    elif filt == "fetes":
        tasks = tasks.filter(done=True)
    else:
        filt = "pendents"
        tasks = tasks.filter(done=False)

    # Filtre per projecte: "tots" (per defecte), "cap" o el pk d'un projecte.
    project_filter = request.GET.get("projecte", "tots")
    current_project = None
    if project_filter == "cap":
        tasks = tasks.filter(project__isnull=True)
    elif project_filter != "tots":
        try:
            project_pk = int(project_filter)
        except ValueError:
            current_project = None
            project_filter = "tots"  # valor no vàlid: mostrem tots
        else:
            current_project = get_object_or_404(
                Project, pk=project_pk, user=request.user
            )
            tasks = tasks.filter(project=current_project)

    return render(
        request,
        "tasks/task_list.html",
        {
            "tasks": tasks,
            "projects": Project.objects.filter(user=request.user),
            "current_filter": filt,
            "project_filter": project_filter,
            "current_project": current_project,
        },
    )


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, "Tasca creada.")
            return redirect(_list_url(request))
    else:
        form = TaskForm(user=request.user)

    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "editing": False, "back_url": _list_url(request)},
    )


def _get_own_task(request, pk: int) -> Task:
    """Carrega la tasca només si pertany a l'usuari actual (404 altrament)."""
    return get_object_or_404(Task, pk=pk, user=request.user)


@login_required
def task_edit(request, pk):
    task = _get_own_task(request, pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tasca actualitzada.")
            return redirect(_list_url(request))
    else:
        form = TaskForm(instance=task, user=request.user)

    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "task": task, "editing": True, "back_url": _list_url(request)},
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
    return redirect(_list_url(request))


@login_required
def task_delete(request, pk):
    task = _get_own_task(request, pk)

    if request.method == "POST":
        task.delete()
        messages.success(request, "Tasca esborrada.")
        return redirect(_list_url(request))

    return render(
        request,
        "tasks/task_confirm_delete.html",
        {"task": task, "back_url": _list_url(request)},
    )


@login_required
def project_list(request):
    """Llista els projectes de l'usuari amb el recompte de tasques."""
    projects = (
        Project.objects.filter(user=request.user)
        .annotate(
            num_tasks=Count("tasks"),
            num_pending=Count("tasks", filter=Q(tasks__done=False)),
        )
    )

    return render(request, "tasks/project_list.html", {"projects": projects})


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, "Projecte creat.")
            return redirect("tasks:project_list")
    else:
        form = ProjectForm(user=request.user)

    return render(request, "tasks/project_form.html", {"form": form, "editing": False})


def _get_own_project(request, pk: int) -> Project:
    """Carrega el projecte només si pertany a l'usuari actual (404 altrament)."""
    return get_object_or_404(Project, pk=pk, user=request.user)


@login_required
def project_edit(request, pk):
    project = _get_own_project(request, pk)

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Projecte actualitzat.")
            return redirect("tasks:project_list")
    else:
        form = ProjectForm(instance=project, user=request.user)

    return render(
        request,
        "tasks/project_form.html",
        {"form": form, "project": project, "editing": True},
    )


@login_required
def project_delete(request, pk):
    """Al esborrar el projecte, les seves tasques queden sense projecte."""
    project = _get_own_project(request, pk)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Projecte esborrat. Les seves tasques continuen sense projecte.")
        return redirect("tasks:project_list")

    return render(request, "tasks/project_confirm_delete.html", {"project": project})
