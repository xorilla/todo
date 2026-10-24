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

    def test_toggle_marks_done_and_undone(self):
        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertTrue(self.task.done)

        self.client.post(reverse("tasks:toggle", args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertFalse(self.task.done)

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
        Task.objects.create(user=self.user, title="Feta", done=True)
        self.assertContains(
            self.client.get(reverse("tasks:list") + "?filtre=pendents"), "Comprar pa"
        )
        response = self.client.get(reverse("tasks:list") + "?filtre=fetes")
        self.assertContains(response, "Feta")
        self.assertNotContains(response, "Comprar pa")

    def test_default_shows_pending_tasks(self):
        """Sense paràmetre, la llista mostra només les pendents."""
        Task.objects.create(user=self.user, title="Ja feta", done=True)
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Comprar pa")
        self.assertNotContains(response, "Ja feta")

    def test_filter_totes_shows_everything(self):
        Task.objects.create(user=self.user, title="Ja feta", done=True)
        response = self.client.get(reverse("tasks:list") + "?filtre=totes")
        self.assertContains(response, "Comprar pa")
        self.assertContains(response, "Ja feta")


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
        Task.objects.create(user=self.user, project=project, title="Parets", done=True)
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
        Task.objects.create(user=self.user, title="Ja feta", done=True)

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
