from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Task

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
