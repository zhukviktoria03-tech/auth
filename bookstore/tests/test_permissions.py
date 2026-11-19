"""Право доступу вашого варіанта: дозволений і заборонений випадок для кожного правила."""
from .base import BookstoreTestCase, only_for


class PermissionMixin(BookstoreTestCase):
    def status(self, user, method, url, data=None):
        client = self.client_for(user)
        response = getattr(client, method)(url, data, format="json") if data is not None \
            else getattr(client, method)(url)
        return response.status_code


@only_for(permission="P1")
class P1EduDomainTests(PermissionMixin):
    def test_anonymous_reads(self):
        self.assertEqual(self.status(None, "get", self.list_url), 200)

    def test_edu_user_creates(self):
        self.assertEqual(self.status(self.alice, "post", self.list_url, self.payload()), 201)

    def test_non_edu_user_cannot_create(self):
        self.assertEqual(self.status(self.carol, "post", self.list_url, self.payload()), 403)

    def test_non_edu_user_cannot_update(self):
        self.assertEqual(self.status(self.carol, "patch", self.detail_url(), {"title": "X"}), 403)

    def test_edu_check_is_on_domain_not_substring(self):
        for email in ["carol@edu.ua.example.com", "carol@notedu.ua"]:
            self.carol.email = email
            self.carol.save(update_fields=["email"])
            self.assertEqual(
                self.status(self.carol, "post", self.list_url, self.payload()), 403,
                f"{email} — не домен .edu.ua",
            )

    def test_edu_check_ignores_case(self):
        self.carol.email = "Carol@KPI.EDU.UA"
        self.carol.save(update_fields=["email"])
        self.assertEqual(self.status(self.carol, "post", self.list_url, self.payload()), 201)

    def test_edu_user_updates(self):
        self.assertEqual(self.status(self.bob, "patch", self.detail_url(), {"title": "X"}), 200)


@only_for(permission="P2")
class P2ClosedCatalogTests(PermissionMixin):
    def test_anonymous_cannot_read(self):
        self.assertEqual(self.status(None, "get", self.list_url), 401)

    def test_user_reads_and_creates(self):
        self.assertEqual(self.status(self.carol, "get", self.list_url), 200)
        self.assertEqual(self.status(self.carol, "post", self.list_url, self.payload()), 201)

    def test_user_updates(self):
        self.assertEqual(self.status(self.carol, "patch", self.detail_url(), {"title": "X"}), 200)

    def test_regular_user_cannot_delete(self):
        self.assertEqual(self.status(self.alice, "delete", self.detail_url()), 403)

    def test_staff_deletes(self):
        self.assertEqual(self.status(self.staff, "delete", self.detail_url()), 204)


@only_for(permission="P3")
class P3OwnerOrModeratorTests(PermissionMixin):
    def test_anonymous_reads(self):
        self.assertEqual(self.status(None, "get", self.detail_url()), 200)

    def test_any_user_creates(self):
        self.assertEqual(self.status(self.carol, "post", self.list_url, self.payload()), 201)

    def test_owner_updates(self):
        self.assertEqual(self.status(self.alice, "patch", self.detail_url(), {"title": "X"}), 200)

    def test_stranger_cannot_update_or_delete(self):
        self.assertEqual(self.status(self.bob, "patch", self.detail_url(), {"title": "X"}), 403)
        self.assertEqual(self.status(self.bob, "delete", self.detail_url()), 403)

    def test_moderator_updates_and_deletes(self):
        self.assertEqual(self.status(self.moder, "patch", self.detail_url(), {"title": "X"}), 200)
        self.assertEqual(self.status(self.moder, "delete", self.detail_url()), 204)


@only_for(permission="P4")
class P4ModelPermsProbationTests(PermissionMixin):
    def test_anonymous_reads(self):
        self.assertEqual(self.status(None, "get", self.list_url), 200)

    def test_user_without_perms_cannot_create(self):
        self.assertEqual(self.status(self.carol, "post", self.list_url, self.payload()), 403)

    def test_new_account_cannot_create_even_with_perms(self):
        self.assertEqual(self.status(self.newbie, "post", self.list_url, self.payload()), 403)

    def test_old_account_with_perms_writes(self):
        self.assertEqual(self.status(self.alice, "post", self.list_url, self.payload()), 201)
        self.assertEqual(self.status(self.bob, "patch", self.detail_url(), {"title": "X"}), 200)

    def test_perms_come_from_db_not_from_token(self):
        header = self.credentials_for(self.carol)  # токен видано ДО того, як з'явилось право
        from django.contrib.auth.models import Group

        self.carol.groups.add(Group.objects.get(name="Editors"))
        self.client.credentials(HTTP_AUTHORIZATION=header)
        self.assertEqual(self.client.post(self.list_url, self.payload(), format="json").status_code, 201)
