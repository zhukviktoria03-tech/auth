"""Інтеграційна вимога вашого варіанта: автентифікація разом із тим, що вже було в API."""
import io
import shutil
import tempfile
from decimal import Decimal

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from bookstore.models import Author, Book

from .base import BookstoreTestCase, only_for


@only_for(integration="I1")
class I1NestedAuthorTests(BookstoreTestCase):
    def test_read_gives_nested_author_and_owner_name(self):
        body = self.client_for(self.alice).get(self.detail_url()).json()
        self.assertEqual(body["author"], {"id": self.author.pk, "name": "Леся Українка"})
        self.assertEqual(body["owner"], "alice")
        self.assertNotIn("author_id", body, "author_id — лише для запису")

    def test_write_takes_author_id(self):
        response = self.client_for(self.alice).post(
            self.list_url, {"title": "Нова", "price": "10.00", "author_id": self.author.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["author"]["name"], "Леся Українка")

    def test_unknown_author_id_is_400(self):
        response = self.client_for(self.alice).post(
            self.list_url, {"title": "Нова", "price": "10.00", "author_id": 999999}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("author_id", response.json())

    def count_list_queries(self, total_books):
        Book.objects.exclude(pk=self.book.pk).delete()
        for i in range(total_books - 1):
            author = Author.objects.create(name=f"Автор {i}")
            Book.objects.create(title=f"Книга {i}", author=author, price=Decimal("1"), owner=self.bob)
        client = self.client_for(self.alice)
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(client.get(self.list_url).status_code, 200)
        return len(queries)

    def test_no_n_plus_one(self):
        small, big = self.count_list_queries(3), self.count_list_queries(9)
        self.assertEqual(small, big, f"3 книги — {small} запитів, 9 книг — {big}: N+1 на author/owner")


@only_for(integration="I2")
class I2MyBooksTests(BookstoreTestCase):
    mine_url = "/api/v1/books/mine/"

    def setUp(self):
        super().setUp()
        Book.objects.create(title="Python для бекенду", author=self.author, price=Decimal("1"), owner=self.alice)
        Book.objects.create(title="Python для дітей", author=self.author, price=Decimal("1"), owner=self.bob)
        Book.objects.create(title="Камінний хрест", author=self.author, price=Decimal("1"), owner=self.bob)

    def ids(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn("results", body, "відповідь має бути з пагінацією: count/next/previous/results")
        return {item["id"] for item in body["results"]}

    def test_anonymous_gets_401(self):
        self.assertEqual(self.client_for().get(self.mine_url).status_code, 401)

    def test_only_own_books(self):
        expected = set(Book.objects.filter(owner=self.alice).values_list("id", flat=True))
        self.assertEqual(self.ids(self.client_for(self.alice).get(self.mine_url)), expected)

    def test_search_works_inside_mine(self):
        found = self.ids(self.client_for(self.bob).get(self.mine_url, {"search": "Python"}))
        self.assertEqual(found, set(Book.objects.filter(owner=self.bob, title__startswith="Python")
                                    .values_list("id", flat=True)))

    def test_general_list_still_shows_everything(self):
        response = self.client_for(self.alice).get(self.list_url)
        self.assertEqual(response.json()["count"], Book.objects.count())


PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@only_for(integration="I3")
class I3CoverUploadTests(BookstoreTestCase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def cover_url(self):
        return f"/api/v1/books/{self.book.pk}/cover/"

    def upload(self, user):
        image = io.BytesIO(PNG_1x1)
        image.name = "cover.png"
        return self.client_for(user).post(self.cover_url(), {"cover": image}, format="multipart")

    def test_owner_uploads(self):
        response = self.upload(self.alice)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["cover"].startswith("http://testserver/media/"))
        self.book.refresh_from_db()
        self.assertTrue(self.book.cover.name.endswith(".png"))

    def test_not_owner_gets_403(self):
        self.assertEqual(self.upload(self.bob).status_code, 403)

    def test_moderator_and_staff_are_not_owners(self):
        self.assertEqual(self.upload(self.moder).status_code, 403, "модератор — не власник")
        self.assertEqual(self.upload(self.staff).status_code, 403, "адміністратор — не власник")

    def test_anonymous_gets_401(self):
        self.assertEqual(self.upload(None).status_code, 401)

    def test_json_is_415(self):
        response = self.client_for(self.alice).post(self.cover_url(), {"cover": "x"}, format="json")
        self.assertEqual(response.status_code, 415)


@only_for(integration="I4")
class I4RoleBasedPageSizeTests(BookstoreTestCase):
    def setUp(self):
        super().setUp()
        Book.objects.bulk_create(
            Book(title=f"Книга {i}", author=self.author, price=Decimal("1"), owner=self.bob) for i in range(29)
        )

    def test_anonymous_gets_5(self):
        body = self.client_for().get(self.list_url).json()
        self.assertEqual(body["count"], 30)
        self.assertEqual(len(body["results"]), 5)

    def test_user_gets_20(self):
        body = self.client_for(self.alice).get(self.list_url).json()
        self.assertEqual(body["count"], 30)
        self.assertEqual(len(body["results"]), 20)
        self.assertIn("page=2", body["next"])


@only_for(integration="I5")
class I5CorsTests(BookstoreTestCase):
    frontend = "http://localhost:3000"

    def preflight(self, origin):
        return self.client_for().options(
            self.list_url,
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization, content-type, x-client-version",
        )

    def test_preflight_from_frontend(self):
        response = self.preflight(self.frontend)
        self.assertEqual(response.status_code, 200, "preflight не несе Authorization і не може отримати 401")
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), self.frontend)
        allowed = response.headers.get("Access-Control-Allow-Headers", "").lower()
        for header in ["authorization", "content-type", "x-client-version"]:
            self.assertIn(header, allowed)

    def test_foreign_origin_gets_no_permission(self):
        response = self.preflight("http://evil.example")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_cors_headers_survive_common_middleware_redirect(self):
        response = self.client_for().get("/api/v1/books", HTTP_ORIGIN=self.frontend)  # без слеша
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"), self.frontend,
            "Редирект від CommonMiddleware пішов без CORS: CorsMiddleware має стояти вище за нього",
        )

    def test_no_wildcard(self):
        response = self.client_for(self.alice).get(self.list_url, HTTP_ORIGIN=self.frontend)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), self.frontend)
