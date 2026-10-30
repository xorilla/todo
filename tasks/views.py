from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
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
    """URL de la llista amb els filtres de la petició actual (si n'hi ha).

    El paràmetre "pare" (de crear subtasques) no es conserva: no és un filtre.
    """
    url = reverse("tasks:list")
    query = request.GET.copy()
    query.pop("pare", None)
    encoded = query.urlencode()
    return f"{url}?{encoded}" if encoded else url


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user, parent__isnull=True)
    tasks = tasks.prefetch_related("subtasks")

    # Sense paràmetre es mostren les no completades ("totes" per veure-les totes).
    filt = request.GET.get("filtre", "")
    if filt == "totes":
        filt = "totes"
    elif filt == "proces":
        tasks = tasks.filter(status=Task.Status.IN_PROGRESS)
    elif filt == "fetes":
        tasks = tasks.filter(status=Task.Status.DONE)
    else:
        filt = "pendents"
        tasks = tasks.exclude(status=Task.Status.DONE)

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


def _get_own_task(request, pk: int) -> Task:
    """Carrega la tasca només si pertany a l'usuari actual (404 altrament)."""
    return get_object_or_404(Task, pk=pk, user=request.user)


def _parent_from_request(request) -> Task | None:
    """Carrega la tasca pare indicada amb `pare=<pk>`.

    Només l'accepta si és de l'usuari i és una tasca arrel: només un nivell
    de jerarquia, les subtasques no poden tenir subtasques.
    """
    pare_pk = request.GET.get("pare")
    if pare_pk is None:
        return None
    try:
        parent = _get_own_task(request, int(pare_pk))
    except ValueError:
        return None
    if parent.parent_id is not None:
        raise Http404("Una subtasca no pot tenir subtasques.")
    return parent


@login_required
def task_create(request):
    parent = _parent_from_request(request)

    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user, parent=parent)
        if form.is_valid():
            task = form.save(commit=False)
            if parent is not None:
                # Formulari sense projecte: l'heretem del pare per consistència.
                task.user = parent.user
                task.project = parent.project
            else:
                task.user = request.user
            task.save()
            if parent is not None:
                messages.success(request, "Subtasca creada.")
            else:
                messages.success(request, "Tasca creada.")
            return redirect(_list_url(request))
    else:
        form = TaskForm(user=request.user, parent=parent)

    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "editing": False,
            "parent": parent,
            "back_url": _list_url(request),
        },
    )


@login_required
def task_edit(request, pk):
    task = _get_own_task(request, pk)

    if request.method == "POST":
        # Si la petició no inclou el camp de data (p. ex. un POST fet de fora
        # del formulari), es conserva la data que ja tenia la tasca: enviar
        # "" explícitament sí que l'esborra.
        data = request.POST
        if "due_date" not in data and task.due_date:
            data = data.copy()
            data["due_date"] = task.due_date
        old_project_id = task.project_id
        form = TaskForm(data, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            # Com que les subtasques hereden el projecte del pare, si es mou
            # el pare de projecte les subtasques s'hi van amb ell.
            if task.subtasks.count() and task.project_id != old_project_id:
                task.subtasks.update(project=task.project)
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
    """Avança la tasca al següent estat: pendent → en procés → completada.

    En completar una tasca, les seves subtasques es completen també; en
    tornar-la a posar pendent, en canvi, no es rescaten: queden com estan.
    """
    task = _get_own_task(request, pk)
    new_status = task.advance_state()
    subs = task.subtasks.exclude(status=Task.Status.DONE) if new_status == Task.Status.DONE else Task.objects.none()
    new_subtasks = subs.count()
    with transaction.atomic():
        if new_subtasks:
            # Propagació cap avall: només les que encara no estaven fetes.
            subs.update(
                status=Task.Status.DONE,
                updated_at=timezone.now(),
            )
        task.save(update_fields=["status", "updated_at"])
    if new_status == Task.Status.IN_PROGRESS:
        messages.info(request, "Tasca iniciada. Endavant!")
    elif new_status == Task.Status.DONE:
        messages.success(request, "Tasca completada. Bona feina!")
        if new_subtasks == 1:
            messages.info(request, "La seva subtasca també s'ha completat.")
        elif new_subtasks:
            messages.info(
                request, f"També s'han completat les {new_subtasks} subtasques."
            )
    else:
        messages.info(request, "Tasca tornada a posar com a pendent.")
    return redirect(_list_url(request))


@login_required
def task_delete(request, pk):
    task = _get_own_task(request, pk)

    if request.method == "POST":
        num_subtasks = task.subtasks.count()
        task.delete()
        if num_subtasks == 0:
            messages.success(request, "Tasca esborrada.")
        elif num_subtasks == 1:
            messages.success(request, "Tasca esborrada, i també la seva subtasca.")
        else:
            messages.success(
                request, f"Tasca esborrada, i també les {num_subtasks} subtasques."
            )
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
            num_pending=Count(
                "tasks", filter=Q(tasks__status=Task.Status.PENDING)
            ),
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
