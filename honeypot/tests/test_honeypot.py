from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from honeypot.app_settings import HONEYPOT_LOGIN_TRYOUT
from honeypot.models.black_list import BlackList
from honeypot.models.login_attempt import LoginAttempt

ATTACKER = "203.0.113.66"
VICTIM = "198.51.100.10"


@override_settings(TRUSTED_PROXY_COUNT=1)
class HoneypotTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def attack(self, client, times):
        for _ in range(times):
            client.post("/admin/login/", {"username": "a@example.com", "password": "x"})

    def test_fake_admin_blacklists_the_attacker(self):
        # nginx appends the address it saw: the last X-Forwarded-For entry
        attacker = Client(HTTP_X_FORWARDED_FOR=ATTACKER)
        self.attack(attacker, HONEYPOT_LOGIN_TRYOUT)

        self.assertTrue(BlackList.objects.filter(ip_address=ATTACKER).exists())
        self.assertEqual(attacker.get("/healthcheck/").status_code, 403)
        self.assertEqual(Client(HTTP_X_FORWARDED_FOR=VICTIM).get("/healthcheck/").status_code, 200)

    def test_forged_forwarded_for_cannot_blacklist_someone_else(self):
        # The attacker writes the victim's address; nginx appends the real one
        attacker = Client(HTTP_X_FORWARDED_FOR=f"{VICTIM}, {ATTACKER}")
        self.attack(attacker, HONEYPOT_LOGIN_TRYOUT)

        self.assertFalse(BlackList.objects.filter(ip_address=VICTIM).exists())
        self.assertEqual(set(LoginAttempt.objects.values_list("ip_address", flat=True)), {ATTACKER})

    def test_blacklist_is_cached_and_refreshed(self):
        client = Client(HTTP_X_FORWARDED_FOR=VICTIM)
        client.get("/healthcheck/")  # warms the cache

        with self.assertNumQueries(0):
            self.assertEqual(client.get("/healthcheck/").status_code, 200)

        entry = BlackList.objects.create(ip_address=VICTIM)
        self.assertEqual(client.get("/healthcheck/").status_code, 403)
        entry.delete()
        self.assertEqual(client.get("/healthcheck/").status_code, 200)

    def test_honeypot_pages(self):
        client = Client()
        self.assertEqual(client.get("/admin/").status_code, 302)
        self.assertEqual(client.get("/admin/login/").status_code, 200)

    def test_empty_address_is_never_blacklisted(self):
        from honeypot.models.black_list import is_blacklisted

        self.assertFalse(is_blacklisted(""))

    def test_attempts_beyond_the_limit_are_not_stored(self):
        # bulk_create skips the signal that blacklists, as an admin cleanup would
        LoginAttempt.objects.bulk_create(
            [LoginAttempt(id=str(n), username="bot", ip_address=ATTACKER) for n in range(HONEYPOT_LOGIN_TRYOUT)]
        )
        self.attack(Client(HTTP_X_FORWARDED_FOR=ATTACKER), 1)
        self.assertEqual(LoginAttempt.objects.filter(ip_address=ATTACKER).count(), HONEYPOT_LOGIN_TRYOUT)
