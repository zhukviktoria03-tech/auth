"""Схема автентифікації: вхід, правильний префікс, вихід (відкликання)."""
from .base import PASSWORD, BookstoreTestCase, only_for


@only_for(scheme="token")
class TokenSchemeTests(BookstoreTestCase):
    login_url = "/api/v1/auth/token/"
    logout_url = "/api/v1/auth/token/logout/"

    def login(self):
        response = self.client_for().post(
            self.login_url, {"username": "alice", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 200, f"POST {self.login_url}: {response.status_code}")
        self.assertIn("token", response.json())
        return response.json()["token"]

    def test_login_returns_token(self):
        self.login()

    def test_token_prefix_authenticates(self):
        key = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_bearer_prefix_is_rejected(self):
        key = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {key}")
        response = self.client.post(self.list_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 401, "DRF Token приймається лише з префіксом Token")

    def test_challenge_header(self):
        response = self.client_for().post(self.list_url, self.payload(), format="json")
        self.assertTrue(response.headers.get("WWW-Authenticate", "").startswith("Token"))

    def test_logout_revokes_token(self):
        key = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 204, f"POST {self.logout_url}: {response.status_code}")
        self.assertEqual(
            self.client.get(self.list_url).status_code, 401,
            "Після виходу той самий ключ має давати 401",
        )


@only_for(scheme="jwt")
class JWTSchemeTests(BookstoreTestCase):
    create_url = "/api/v1/auth/jwt/create/"
    refresh_url = "/api/v1/auth/jwt/refresh/"
    logout_url = "/api/v1/auth/jwt/logout/"

    def login(self):
        response = self.client_for().post(
            self.create_url, {"username": "alice", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 200, f"POST {self.create_url}: {response.status_code}")
        body = response.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        return body

    def test_access_lives_15_minutes(self):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken(self.login()["access"])
        self.assertEqual(token["exp"] - token["iat"], 15 * 60, "ACCESS_TOKEN_LIFETIME має бути 15 хвилин")

    def test_bearer_prefix_authenticates(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login()['access']}")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_refresh_token_is_not_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login()['refresh']}")
        self.assertEqual(self.client.get(self.list_url).status_code, 401)

    def test_challenge_header(self):
        response = self.client_for().post(self.list_url, self.payload(), format="json")
        self.assertTrue(response.headers.get("WWW-Authenticate", "").startswith("Bearer"))

    def test_refresh_then_logout_blacklists(self):
        pair = self.login()
        refreshed = self.client_for().post(self.refresh_url, {"refresh": pair["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 200, f"POST {self.refresh_url}: {refreshed.status_code}")
        self.assertIn("access", refreshed.json())
        refresh = refreshed.json().get("refresh", pair["refresh"])  # з ротацією приходить новий

        logout = self.client_for().post(self.logout_url, {"refresh": refresh}, format="json")
        self.assertEqual(logout.status_code, 200, f"POST {self.logout_url}: {logout.status_code}")

        again = self.client_for().post(self.refresh_url, {"refresh": refresh}, format="json")
        self.assertEqual(again.status_code, 401, "Refresh після виходу має бути в чорному списку")
