"""Тестові дані для ручної перевірки curl-ом: python manage.py seed

Усі паролі — pass12345 (крім admin / admin). Команду можна запускати повторно.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.utils import timezone

from bookstore.models import Author, Book

PASSWORD = "pass12345"

# username: (email, днів від реєстрації, групи, is_staff)
USERS = {
    "alice": ("alice@kpi.edu.ua", 30, ["Editors"], False),
    "bob": ("bob@lnu.edu.ua", 30, ["Editors"], False),
    "carol": ("carol@gmail.com", 30, [], False),
    "newbie": ("newbie@kpi.edu.ua", 0, ["Editors"], False),
    "moder": ("moder@gmail.com", 30, ["Moderators"], False),
    "staff": ("staff@gmail.com", 30, [], True),
}

AUTHORS = ["Тарас Шевченко", "Леся Українка", "Іван Франко", "Ліна Костенко", "Сергій Жадан"]


class Command(BaseCommand):
    help = "Створює користувачів, групи, авторів і 30 книг для ручної перевірки"

    def handle(self, *args, **options):
        User = get_user_model()
        now = timezone.now()

        editors, _ = Group.objects.get_or_create(name="Editors")
        editors.permissions.set(
            Permission.objects.filter(
                content_type__app_label="bookstore",
                codename__in=["add_book", "change_book", "delete_book"],
            )
        )
        Group.objects.get_or_create(name="Moderators")

        admin, created = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@example.com"}
        )
        admin.is_staff = admin.is_superuser = True
        admin.set_password("admin")
        admin.save()

        users = {}
        for username, (email, days, groups, is_staff) in USERS.items():
            user, _ = User.objects.get_or_create(username=username)
            user.email = email
            user.is_staff = is_staff
            user.date_joined = now - timedelta(days=days)
            user.set_password(PASSWORD)
            user.save()
            user.groups.set(Group.objects.filter(name__in=groups))
            users[username] = user

        authors = [Author.objects.get_or_create(name=name)[0] for name in AUTHORS]

        if not Book.objects.exists():
            owners = [users["alice"], users["bob"], users["carol"]]
            Book.objects.bulk_create(
                Book(
                    title=f"Книга {i:02d}" if i % 3 else f"Python для бекенду, том {i // 3}",
                    author=authors[i % len(authors)],
                    price=Decimal(100 + i * 10),
                    owner=owners[i % len(owners)],
                )
                for i in range(1, 31)
            )

        self.stdout.write(self.style.SUCCESS(
            f"Готово: {User.objects.count()} користувачів, {Book.objects.count()} книг. "
            f"Паролі: {PASSWORD} (admin / admin)."
        ))
