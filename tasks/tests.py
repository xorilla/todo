from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Project, Task

PASSWORD = "pass-testing-123"


class AuthTests(TestCase):
    def test_list_requires_login(self):
        """La llista redirigeix a login si no ets sessió."""
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "nou_usuari",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
            follow=True,
        )
        self.assertTrue(User.objects.filter(username="nou_usuari").exists())
        self.assertTrue(response.context["user"].is_authenticated)

    def test_register_rejects_weak_password(self):
        self.client.post(
            reverse("register"),
            {"username": "feble", "password1": "123", "password2": "123"},
        )
        self.assertFalse(User.objects.filter(username="feble").exists())


class TaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("anna", password=PASSWORD)
        self.other = User.objects.create_user("pere", password=PASSWORD)
        self.client.force_login(self.user)
        self.task = Task.objects.create(user=self.user, title="Comprar pa")

    def test_list_shows_own_tasks(self):
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Comprar pa")

    def test_list_does_not_show_other_users_tasks(self):
        Task.objects.create(user=self.other, title="Tasca aliena")
        response = self.client.get(reverse("tasks:list"))
        self.assertNotContains(response, "Tasca aliena")

    def test_create_task(self):
        response = self.client.post(
            reverse("tasks:create"),
            {"title": "Regar les plantes", "notes": "Cada dimarts", "due_date": ""},
            follow=True,
        )
        self.assertTrue(Task.objects.filter(title="Regar les plantes").exists())
        task = Task.objects.get(title="Regar les plantes")
        self.assertEqual(task.user, self.user)
        self.assertContains(response, "Regar les plantes")

    def test_edit_task(self):
        response = self.client.post(
            reverse("tasks:edit", args=[self.task.pk]),
            {"title": "Comprar pa integral", "notes": "", "due_date": ""},
            follow=True,
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Comprar pa integral")
        self.assertContains(response, "Comprar pa integral")

    def test_edit_form_shows_date_in_iso_format(self):
        """El valor de la data s'ha de renderitzar en ISO per al widget date."""
        self.task.due_date = date(2026, 3, 14)
        self.task.save()
        response = self.client.get(reverse("tasks:edit", args=[self.task.pk]))
        self.assertContains(response, 'value="2026-03-14"')

    def test_edit_keeps_due_date_when_sent_unchanged(self):
        """Editar sense canviar la data conserva la data anterior."""
        self.task.due_date = date(2026, 3, 14)
        self.task.save()
        self.client.post(
            reverse("tasks:edit", args=[self.task.pk]),
            {"title": "Comprar pa", "notes": "", "due_date": "2026-03-14"},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_date, date(2026, 3, 14))

    def test_edit_keeps_due_date_when_field_not_sent(self):
        """Si el POST no inclou el camp de data, es conserva la que ja tenia."""
        self.task.due_date = date(2026, 3, 14)
        self.task.save()
        self.client.post(
            reverse("tasks:edit", args=[self.task.pk]),
            {"title": "Comprar pa", "notes": ""},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_date, date(2026, 3, 14))

    def test_edit_can_clear_due_date(self):
        """Enviar el camp de data buit explicitament esborra la data."""
        self.task.due_date = date(2026, 3, 14)
        self.task.save()
        self.client.post(
            reverse("tasks:edit", args=[self.task.pk]),
            {"title": "Comprar pa", "notes": "", "due_date": ""},
        )
        self.task.refresh_from_db()
        self.assertIsNone(self.task.due_date)

    def test_toggle_advances_through_states(self):
        """El botó cicle pendent → en procés → completada → pendent."""
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)

        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)

    def test_new_task_starts_pending(self):
        self.assertEqual(self.task.status, Task.Status.PENDING)

    def test_delete_task_with_confirmation(self):
        # GET mostra la confirmació i no esborra res
        response = self.client.get(reverse("tasks:delete", args=[self.task.pk]))
        self.assertContains(response, "Comprar pa")
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

        # POST esborra
        self.client.post(reverse("tasks:delete", args=[self.task.pk]))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_cannot_touch_other_users_task(self):
        foreign = Task.objects.create(user=self.other, title="Tasca aliena")
        for url in (
            lambda: reverse("tasks:edit", args=[foreign.pk]),
            lambda: reverse("tasks:toggle", args=[foreign.pk]),
            lambda: reverse("tasks:delete", args=[foreign.pk]),
        ):
            response = self.client.post(url())
            self.assertEqual(response.status_code, 404)

    def test_filter_by_state(self):
        Task.objects.create(user=self.user, title="Feta", status=Task.Status.DONE)
        self.assertContains(
            self.client.get(reverse("tasks:list") + "?filtre=pendents"), "Comprar pa"
        )
        response = self.client.get(reverse("tasks:list") + "?filtre=fetes")
        self.assertContains(response, "Feta")
        self.assertNotContains(response, "Comprar pa")

    def test_filter_en_proces(self):
        Task.objects.create(
            user=self.user, title="En curs", status=Task.Status.IN_PROGRESS
        )
        response = self.client.get(reverse("tasks:list") + "?filtre=proces")
        self.assertContains(response, "En curs")
        self.assertNotContains(response, "Comprar pa")

    def test_default_shows_pending_tasks(self):
        """Sense paràmetre, la llista mostra les pendents i les en procés."""
        Task.objects.create(
            user=self.user, title="Ja feta", status=Task.Status.DONE
        )
        Task.objects.create(
            user=self.user, title="Trencada", status=Task.Status.IN_PROGRESS
        )
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Comprar pa")
        self.assertContains(response, "Trencada")
        self.assertNotContains(response, "Ja feta")

    def test_filter_totes_shows_everything(self):
        Task.objects.create(user=self.user, title="Ja feta", status=Task.Status.DONE)
        response = self.client.get(reverse("tasks:list") + "?filtre=totes")
        self.assertContains(response, "Comprar pa")
        self.assertContains(response, "Ja feta")

    def test_header_nav_links_to_tasks_and_projects(self):
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, f'href="{reverse("tasks:list")}"')
        self.assertContains(response, f'href="{reverse("tasks:project_list")}"')

    def test_nav_highlights_current_section(self):
        response = self.client.get(
            reverse("tasks:list") + "?filtre=totes"
        )
        self.assertContains(
            response, f'<a class="navlink active" href="{reverse("tasks:list")}">Tasques</a>'
        )

        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(
            response,
            f'<a class="navlink active" href="{reverse("tasks:project_list")}">Projectes</a>',
        )
        self.assertNotContains(
            response,
            f'<a class="navlink active" href="{reverse("tasks:list")}">Tasques</a>',
        )


class ProjectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("anna", password=PASSWORD)
        self.other = User.objects.create_user("pere", password=PASSWORD)
        self.client.force_login(self.user)

    def test_create_project(self):
        response = self.client.post(
            reverse("tasks:project_create"), {"name": "Casa"}, follow=True
        )
        self.assertTrue(Project.objects.filter(name="Casa").exists())
        self.assertEqual(Project.objects.get(name="Casa").user, self.user)
        self.assertContains(response, "Casa")

    def test_create_project_rejects_duplicated_name(self):
        Project.objects.create(user=self.user, name="Casa")
        response = self.client.post(reverse("tasks:project_create"), {"name": "Casa"})
        self.assertEqual(
            Project.objects.filter(user=self.user, name="Casa").count(), 1
        )
        self.assertContains(response, "Ja tens un projecte amb aquest nom")

    def test_edit_project(self):
        project = Project.objects.create(user=self.user, name="Feina")
        response = self.client.post(
            reverse("tasks:project_edit", args=[project.pk]),
            {"name": "Feina de tardor"},
            follow=True,
        )
        project.refresh_from_db()
        self.assertEqual(project.name, "Feina de tardor")
        self.assertContains(response, "Feina de tardor")

    def test_delete_project_unassigns_its_tasks(self):
        """Al esborrar un projecte, les seves tasques queden sense projecte."""
        project = Project.objects.create(user=self.user, name="Feina")
        task = Task.objects.create(user=self.user, project=project, title="Fer informe")

        # GET mostra la confirmació i no esborra res
        response = self.client.get(reverse("tasks:project_delete", args=[project.pk]))
        self.assertContains(response, "«Feina»")
        self.assertContains(response, "sense projecte")
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())

        # POST esborra el projecte però no la tasca
        self.client.post(reverse("tasks:project_delete", args=[project.pk]))
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())
        task.refresh_from_db()
        self.assertIsNone(task.project)
        self.assertEqual(task.title, "Fer informe")

    def test_cannot_touch_other_users_project(self):
        foreign = Project.objects.create(user=self.other, name="Aliena")
        for url_name in ("tasks:project_edit", "tasks:project_delete"):
            response = self.client.post(
                reverse(url_name, args=[foreign.pk]), {"name": "Robat"}
            )
            self.assertEqual(response.status_code, 404)
        self.assertEqual(
            Project.objects.filter(user=self.other, name="Aliena").count(), 1
        )

    def test_cannot_create_task_with_foreign_project(self):
        foreign = Project.objects.create(user=self.other, name="Aliena")
        response = self.client.post(
            reverse("tasks:create"),
            {"title": "Intrusa", "project": foreign.pk, "due_date": ""},
        )
        self.assertFalse(Task.objects.filter(title="Intrusa").exists())
        self.assertTrue(response.context["form"].has_error("project"))

    def test_project_list_shows_counts(self):
        project = Project.objects.create(user=self.user, name="Casa")
        Task.objects.create(user=self.user, project=project, title="Fotos noves")
        Task.objects.create(
            user=self.user, project=project, title="Parets", status=Task.Status.DONE
        )
        Project.objects.create(user=self.other, name="Aliena")
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "Casa")
        self.assertContains(response, "1 pendents · 2 en total")
        self.assertNotContains(response, "Aliena")


class TaskProjectFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("anna", password=PASSWORD)
        self.other = User.objects.create_user("pere", password=PASSWORD)
        self.client.force_login(self.user)
        self.project = Project.objects.create(user=self.user, name="Feina")
        self.foreign = Project.objects.create(user=self.other, name="Aliena")
        self.own_task = Task.objects.create(
            user=self.user, project=self.project, title="Fer informe"
        )
        self.free_task = Task.objects.create(user=self.user, title="Penjar el quadre")
        Task.objects.create(user=self.user, title="Ja feta", status=Task.Status.DONE)

    def test_filter_by_project(self):
        response = self.client.get(reverse("tasks:list") + f"?projecte={self.project.pk}")
        self.assertContains(response, "Fer informe")
        self.assertNotContains(response, "Penjar el quadre")

    def test_filter_tasks_without_project(self):
        response = self.client.get(reverse("tasks:list") + "?projecte=cap")
        self.assertContains(response, "Penjar el quadre")
        self.assertNotContains(response, "Fer informe")

    def test_cannot_filter_by_foreign_project(self):
        response = self.client.get(reverse("tasks:list") + f"?projecte={self.foreign.pk}")
        self.assertEqual(response.status_code, 404)

    def test_invalid_project_filter_falls_back_to_all_projects(self):
        response = self.client.get(reverse("tasks:list") + "?projecte=xxx")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fer informe")
        self.assertContains(response, "Penjar el quadre")

    def test_task_shows_project_label(self):
        response = self.client.get(reverse("tasks:list") + "?filtre=totes")
        self.assertContains(response, "Feina")


class SubtaskTests(TestCase):
    """Un sol nivell de jerarquia: tasca → subtasques (hereten projecte)."""

    def setUp(self):
        self.user = User.objects.create_user("anna", password=PASSWORD)
        self.other = User.objects.create_user("pere", password=PASSWORD)
        self.client.force_login(self.user)
        self.project = Project.objects.create(user=self.user, name="Casa")
        self.task = Task.objects.create(
            user=self.user, project=self.project, title="Netejar el garatge"
        )

    def test_create_subtask_via_url(self):
        response = self.client.post(
            reverse("tasks:create") + f"?pare={self.task.pk}",
            {"title": "Traieu-ho tot", "notes": "", "due_date": ""},
            follow=True,
        )
        sub = Task.objects.get(title="Traieu-ho tot")
        self.assertEqual(sub.parent, self.task)
        # Hereda usuari i projecte del pare.
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.project, self.project)
        self.assertContains(response, "Subtasca creada.")

    def test_subtask_form_has_no_project_field(self):
        response = self.client.get(reverse("tasks:create") + f"?pare={self.task.pk}")
        self.assertNotContains(response, 'name="project"')

    def test_cannot_create_subtask_of_foreign_task(self):
        foreign = Task.objects.create(user=self.other, title="Aliena")
        self.client.post(
            reverse("tasks:create") + f"?pare={foreign.pk}",
            {"title": "Intrusa"},
        )
        self.assertFalse(Task.objects.filter(title="Intrusa").exists())

    def test_cannot_nest_subtask_under_subtask(self):
        parent = Task.objects.create(user=self.user, title="Pare")
        sub = Task.objects.create(user=self.user, parent=parent, title="Fill")
        response = self.client.get(reverse("tasks:create") + f"?pare={sub.pk}")
        self.assertEqual(response.status_code, 404)

    def test_model_rejects_deep_nesting(self):
        """La validació del model també impedeix subtasques de subtasques."""
        from django.core.exceptions import ValidationError as VE

        sub = Task.objects.create(user=self.user, parent=self.task, title="Fill")
        second = Task(user=self.user, parent=sub, title="Net")
        with self.assertRaises(VE):
            second.clean()

    def test_model_rejects_foreign_parent(self):
        from django.core.exceptions import ValidationError as VE

        foreign = Task.objects.create(user=self.other, title="Aliena")
        sub = Task(user=self.user, parent=foreign, title="Robada")
        with self.assertRaises(VE):
            sub.clean()

    def test_list_shows_subtask_nested_under_parent(self):
        Task.objects.create(
            user=self.user, parent=self.task, title="Traieu-ho tot"
        )
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Traieu-ho tot")
        self.assertContains(response, "subtasques completades")

    def test_default_filter_hides_root_done_but_keeps_pending_parent(self):
        """Les subs es mostren dins el pare; el filtre actua a l'arrel."""
        Task.objects.create(
            user=self.user,
            parent=self.task,
            title="Ja feta",
            status=Task.Status.DONE,
        )
        # La pare pendent, amb la seva subtasca feta dins, es mostra així.
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Netejar el garatge")
        self.assertContains(response, "Ja feta")
        # Com a arrel feta, en canvi, el filtre per defecte l'amaga.
        response = self.client.get(reverse("tasks:list") + "?filtre=fetes")
        self.assertNotContains(response, "Netejar el garatge")

    def test_completing_parent_completes_subtasks(self):
        sub = Task.objects.create(user=self.user, parent=self.task, title="Fill")
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))  # en procés
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))  # feta
        sub.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)
        self.assertEqual(sub.status, Task.Status.DONE)

    def test_completed_subtasks_are_not_retagged(self):
        """Les que ja eren completes no es toquen en propagar."""
        sub = Task.objects.create(
            user=self.user,
            parent=self.task,
            title="Ja feta",
            status=Task.Status.DONE,
        )
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))  # en procés
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))  # feta
        sub.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)
        self.assertEqual(sub.status, Task.Status.DONE)

    def test_reverting_parent_does_not_revert_subtasks(self):
        """Tornar el pare a pendent NO rescata les subtasques."""
        sub = Task.objects.create(user=self.user, parent=self.task, title="Fill")
        self.task.status = Task.Status.IN_PROGRESS
        self.task.save()
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))  # pare → feta
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))  # pare → pendent
        sub.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)
        self.assertEqual(sub.status, Task.Status.DONE)

    def test_toggling_subtask_independently(self):
        sub = Task.objects.create(user=self.user, parent=self.task, title="Fill")
        self.client.post(reverse("tasks:toggle", args=[sub.pk]))
        sub.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(sub.status, Task.Status.IN_PROGRESS)
        self.assertEqual(self.task.status, Task.Status.PENDING)

    def test_starting_parent_does_not_start_subtasks(self):
        """Posar el pare en procés no posa les subtasques en procés.

        Cada subtasca s'inicia de manera independent; només la
        finalització es propaga cap avall.
        """
        sub = Task.objects.create(user=self.user, parent=self.task, title="Fill")
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))
        sub.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)
        self.assertEqual(sub.status, Task.Status.PENDING)

    def test_editing_subtask_uses_parent_project(self):
        """Editar una subtasca no toca el projecte heretat del pare."""
        sub = Task.objects.create(
            user=self.user,
            parent=self.task,
            project=self.project,  # al flux real ho posa el formulari
            title="Fill",
        )
        self.client.post(
            reverse("tasks:edit", args=[sub.pk]),
            {"title": "Fill editat", "notes": "", "due_date": ""},
        )
        sub.refresh_from_db()
        self.assertEqual(sub.title, "Fill editat")
        self.assertEqual(sub.project, self.project)

    def test_moving_parent_project_moves_subtasks(self):
        """Al moure el pare de projecte, les subtasques s'hi van amb ell."""
        new_project = Project.objects.create(user=self.user, name="Nau")
        sub = Task.objects.create(user=self.user, parent=self.task, title="Fill")
        self.client.post(
            reverse("tasks:edit", args=[self.task.pk]),
            {
                "title": "Netejar el garatge",
                "notes": "",
                "due_date": "",
                "project": new_project.pk,
            },
            follow=True,
        )
        sub.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.task.project, new_project)
        self.assertEqual(sub.project, new_project)

    def test_delete_parent_deletes_subtasks(self):
        Task.objects.create(user=self.user, parent=self.task, title="Fill 1")
        Task.objects.create(user=self.user, parent=self.task, title="Fill 2")
        response = self.client.get(reverse("tasks:delete", args=[self.task.pk]))
        self.assertContains(response, "les 2 subtasques")
        self.client.post(reverse("tasks:delete", args=[self.task.pk]))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
        self.assertFalse(Task.objects.filter(parent=self.task).exists())

    def test_project_counts_include_subtasks(self):
        """El recompte del projecte tracta les subtasques com tasques."""
        Task.objects.create(
            user=self.user, parent=self.task, project=self.project, title="Fill"
        )
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "2 pendents · 2 en total")
