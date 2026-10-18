"""Nothing in production answers should name the framework behind the API."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import Client, override_settings
from rest_framework.exceptions import ValidationError

from app.rest.exceptions import exception_handler_without_signature
from app.tests.helpers import GraphQLTestCase
from honeypot.models.login_attempt import LoginAttempt
from honeypot.views.login_views import LoginView

DJANGO_COOKIES = {"csrftoken", "sessionid", "messages"}


class NeutralCookiesTestCase(GraphQLTestCase):
    def test_admin_log_in_uses_neutral_cookie_names(self):
        get_user_model().objects.create_superuser("root", "r@example.com", "root-pass-123")
        client = Client()
        page = client.get("/staff/tools/login/")
        token = page.cookies["xsrf"].value
        response = client.post("/staff/tools/login/", {"username": "root", "password": "root-pass-123", "csrfmiddlewaretoken": token})

        self.assertEqual(response.status_code, 302)
        self.assertIn("sid", client.cookies)
        self.assertFalse(DJANGO_COOKIES & set(client.cookies))

    def test_messages_cookie(self):
        client = Client()
        client.post("/admin/login/", {"username": "bot@example.com", "password": "x"})
        self.assertIn("flash", client.cookies)
        self.assertFalse(DJANGO_COOKIES & set(client.cookies))


class PlainErrorPagesTestCase(GraphQLTestCase):
    def test_bodies_are_bare_status_lines(self):
        self.assertEqual(self.client.get("/nothing-here/").content, b"Not Found")
        self.assertEqual(Client(HTTP_HOST="1.2.3.4").get("/healthcheck/").content, b"Bad Request")
        failing = Client(raise_request_exception=False)
        with mock.patch("app.rest.healthcheck.HealthcheckView.get", side_effect=RuntimeError):
            self.assertEqual(failing.get("/healthcheck/").content, b"Internal Server Error")

    def test_forbidden_and_csrf_failure(self):
        with mock.patch.object(LoginView, "get", side_effect=PermissionDenied):
            response = self.client.get("/admin/login/")
        self.assertEqual((response.status_code, response.content), (403, b"Forbidden"))

        strict = Client(enforce_csrf_checks=True)
        response = strict.post("/staff/tools/login/", {"username": "x", "password": "y"})
        self.assertEqual((response.status_code, response.content), (403, b"Forbidden"))


class RestWithoutSignatureTestCase(GraphQLTestCase):
    def test_options_has_no_metadata(self):
        response = self.client.options("/healthcheck/")
        self.assertEqual((response.status_code, response.json()), (405, {"detail": "Method Not Allowed"}))

    def test_cors_preflight_still_works(self):
        response = self.client.options(
            "/drivers/x/upload-documents/",
            HTTP_ORIGIN="http://localhost",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost")

    def test_generic_detail(self):
        response = self.client.post("/drivers/x/upload-documents/")
        self.assertEqual((response.status_code, response.json()), (401, {"detail": "Unauthorized"}))

    @override_settings(DEBUG=True)
    def test_real_detail_while_developing(self):
        response = self.client.post("/drivers/x/upload-documents/")
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_field_errors_are_kept(self):
        response = exception_handler_without_signature(ValidationError(["bad"]), {})
        self.assertEqual(response.data, ["bad"])


class NeutralPagesTestCase(GraphQLTestCase):
    def test_admin_log_in_does_not_name_django(self):
        body = self.client.get("/staff/tools/login/").content.decode()
        self.assertNotIn("Django", body)
        self.assertIn("Administración", body)

    def test_honeypot_has_no_django_markers(self):
        body = self.client.get("/admin/login/").content.decode().lower()
        self.assertNotIn("django", body)
        self.assertNotIn("csrf", body)

    def test_honeypot_takes_posts_without_csrf_token(self):
        strict = Client(enforce_csrf_checks=True, HTTP_X_FORWARDED_FOR="203.0.113.9")
        strict.post("/admin/login/", {"username": "bot@example.com", "password": "x"})
        self.assertTrue(LoginAttempt.objects.filter(ip_address="203.0.113.9").exists())
