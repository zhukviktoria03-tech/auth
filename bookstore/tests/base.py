"""Спільна підготовка для всіх тестів. Не редагуйте цей файл."""
import unittest
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from bookstore.models import Author, Book

from .variants import VARIANTS

PASSWORD = "pass12345"


def current_variant():
    number = getattr(settings, "BOOKSTORE_VARIANT", 0)
    return number, VARIANTS.get(number)


VARIANT_NUMBER, VARIANT = current_variant()


def only_for(**conditions):
    """Пропустити тест, якщо він не стосується вашого варіанта."""
    if VARIANT is None:
        return lambda test: test  # без варіанта тест має впасти, а не пропуститись
    matches = all(VARIANT[key] == value for key, value in conditions.items())
    reason = "не ваш варіант: " + ", ".join(f"{k}={v}" for k, v in conditions.items())
    return unittest.skipUnless(matches, reason)


class BookstoreTestCase(APITestCase):
    """Користувачі й дані, однакові для всіх варіантів.

    alice   — @kpi.edu.ua, акаунт 30 днів, група Editors (add/change/delete_book), власниця книг
    bob     — @lnu.edu.ua, акаунт 30 днів, група Editors, НЕ власник книг alice
    carol   — @gmail.com,  акаунт 30 днів, без груп і прав
    newbie  — @kpi.edu.ua, акаунт створено щойно, група Editors
    moder   — @gmail.com,  група Moderators
    staff   — @gmail.com,  is_staff=True
    """

    list_url = "/api/v1/books/"

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        now = timezone.now()
        editors = Group.objects.create(name="Editors")
        editors.permissions.set(
            Permission.objects.filter(
                content_type__app_label="bookstore",
                codename__in=["add_book", "change_book", "delete_book"],
            )
        )
        moderators = Group.objects.create(name="Moderators")

        def make(username, email, days, groups=(), is_staff=False):
            user = User.objects.create_user(username, email, PASSWORD, is_staff=is_staff)
            user.date_joined = now - timedelta(days=days)
            user.save(update_fields=["date_joined"])
            user.groups.set(groups)
            return user

        cls.alice = make("alice", "alice@kpi.edu.ua", 30, [editors])
        cls.bob = make("bob", "bob@lnu.edu.ua", 30, [editors])
        cls.carol = make("carol", "carol@gmail.com", 30)
        cls.newbie = make("newbie", "newbie@kpi.edu.ua", 0, [editors])
        cls.moder = make("moder", "moder@gmail.com", 30, [moderators])
        cls.staff = make("staff", "staff@gmail.com", 30, is_staff=True)

        cls.author = Author.objects.create(name="Леся Українка")
        cls.book = Book.objects.create(
            title="Лісова пісня", author=cls.author, price=Decimal("250.00"), owner=cls.alice
        )

    def setUp(self):
        if VARIANT is None:
            self.fail(
                f"У core/settings.py BOOKSTORE_VARIANT = {VARIANT_NUMBER!r}. "
                "Впишіть номер свого варіанта (1-16)."
            )
        cache.clear()  # лічильники throttling не повинні переходити між тестами

    # --- допоміжне ---------------------------------------------------------

    def detail_url(self, book=None):
        return f"/api/v1/books/{(book or self.book).pk}/"

    def payload(self, title="Нова книга"):
        # Обидва ключі навмисно: author — для звичайного серіалізатора,
        # author_id — для варіантів I1. Зайвий ключ серіалізатор ігнорує.
        return {"title": title, "price": "150.00", "author": self.author.pk, "author_id": self.author.pk}

    def credentials_for(self, user):
        """Заголовок Authorization для схеми вашого варіанта (без звернення до логіну)."""
        if VARIANT["scheme"] == "token":
            from rest_framework.authtoken.models import Token

            token, _ = Token.objects.get_or_create(user=user)
            return f"Token {token.key}"
        from rest_framework_simplejwt.tokens import RefreshToken

        return f"Bearer {RefreshToken.for_user(user).access_token}"

    def client_for(self, user=None):
        client = APIClient()
        if user is not None:
            client.credentials(HTTP_AUTHORIZATION=self.credentials_for(user))
        return client
