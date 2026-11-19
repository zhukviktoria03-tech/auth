"""Однаково для всіх: анонім не змінює дані і отримує саме 401, а не 403."""
from .base import BookstoreTestCase


class AnonymousWriteTests(BookstoreTestCase):
    def assert_401(self, response):
        self.assertEqual(
            response.status_code, 401,
            f"Очікувався 401, отримано {response.status_code}. Якщо 403 — першим у "
            "DEFAULT_AUTHENTICATION_CLASSES стоїть клас без WWW-Authenticate (сесійний).",
        )
        self.assertIn("WWW-Authenticate", response.headers)

    def test_anonymous_cannot_create(self):
        self.assert_401(self.client_for().post(self.list_url, self.payload(), format="json"))

    def test_anonymous_cannot_update(self):
        self.assert_401(self.client_for().patch(self.detail_url(), {"title": "X"}, format="json"))

    def test_anonymous_cannot_delete(self):
        self.assert_401(self.client_for().delete(self.detail_url()))

    def test_permission_is_custom_class(self):
        from bookstore.views import BookViewSet

        modules = [cls.__module__ for cls in BookViewSet.permission_classes]
        self.assertIn(
            "bookstore.permissions", modules,
            "Право доступу вашого варіанта має бути власним класом у bookstore/permissions.py, "
            "підключеним у BookViewSet.permission_classes",
        )
