"""Ліміти вашого варіанта. Анонім міряється на публічному /authors/, користувач — на /books/."""
from .base import VARIANT, BookstoreTestCase


class ThrottleTests(BookstoreTestCase):
    authors_url = "/api/v1/authors/"

    def test_rates_and_periods(self):
        from rest_framework.settings import api_settings
        from rest_framework.throttling import SimpleRateThrottle

        rates = api_settings.DEFAULT_THROTTLE_RATES
        parse = SimpleRateThrottle.parse_rate
        self.assertEqual(parse(None, rates.get("anon")), (VARIANT["anon_rate"], 3600),
                         "anon: запитів на ГОДИНУ, як у вашому рядку")
        self.assertEqual(parse(None, rates.get("user")), (VARIANT["user_rate"], 86400),
                         "user: запитів на ДОБУ, як у вашому рядку")

    def assert_limit(self, client, url, limit, who):
        for i in range(limit):
            response = client.get(url)
            self.assertEqual(
                response.status_code, 200,
                f"{who}: запит №{i + 1} із дозволених {limit} отримав {response.status_code}",
            )
        response = client.get(url)
        self.assertEqual(response.status_code, 429, f"{who}: запит №{limit + 1} мав отримати 429")
        self.assertIn("Retry-After", response.headers)

    def test_anonymous_rate(self):
        self.assert_limit(self.client_for(), self.authors_url, VARIANT["anon_rate"], "анонім")

    def test_user_rate(self):
        self.assert_limit(self.client_for(self.alice), self.list_url, VARIANT["user_rate"], "alice")

    def test_users_are_counted_separately(self):
        alice = self.client_for(self.alice)
        for _ in range(VARIANT["user_rate"]):
            alice.get(self.list_url)
        self.assertEqual(alice.get(self.list_url).status_code, 429)
        self.assertEqual(self.client_for(self.bob).get(self.list_url).status_code, 200)
