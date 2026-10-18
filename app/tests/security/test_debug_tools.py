"""Debugging tools and details must not exist in production (DEBUG off)."""

import importlib
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import clear_url_caches

import viajes.urls
from app.rest.healthcheck import HealthcheckView
from app.tests.helpers import GraphQLTestCase


def reload_urls():
    clear_url_caches()
    importlib.reload(viajes.urls)


class ProductionHidesDebugToolsTestCase(GraphQLTestCase):
    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_superuser("root", "r@example.com", "root-pass-123")

    def test_graphiql_and_swagger_are_not_routed(self):
        self.client.force_login(self.admin)
        for path in ("/graphiql/", "/staff/tools/swagger/"):
            response = self.client.get(path, HTTP_ACCEPT="text/html")
            self.assertEqual(response.status_code, 404, path)

    def test_graphql_endpoint_never_serves_the_ide(self):
        response = self.client.get("/graphql/", HTTP_ACCEPT="text/html")
        self.assertNotIn(b"graphiql", response.content.lower())

    def test_not_found_page_has_no_debug_details(self):
        response = self.client.get("/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"URLconf", response.content)
        self.assertNotIn(b"INTERNAL_ADMIN_URL", response.content)

    def test_server_error_has_no_traceback(self):
        client = Client(raise_request_exception=False)
        with mock.patch.object(HealthcheckView, "get", side_effect=RuntimeError("secret detail")):
            response = client.get("/healthcheck/")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"secret detail", response.content)
        self.assertNotIn(b"Traceback", response.content)

    def test_graphql_does_not_suggest_field_names(self):
        result = self.gql("query { getTripLis { count } }")
        self.assertEqual(result["errors"], [{"message": "Invalid query."}])

    def test_swagger_app_is_not_loaded(self):
        self.assertNotIn("drf_yasg", settings.INSTALLED_APPS)


@override_settings(DEBUG=True, INSTALLED_APPS=settings.INSTALLED_APPS + ["drf_yasg"])
class DevelopmentKeepsDebugToolsTestCase(GraphQLTestCase):
    def setUp(self):
        super().setUp()
        reload_urls()
        self.addCleanup(reload_urls)  # back to the production routes
        self.admin = get_user_model().objects.create_superuser("root", "r@example.com", "root-pass-123")

    def test_graphiql_for_superusers(self):
        self.assertEqual(self.client.get("/graphiql/").status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/graphiql/", HTTP_ACCEPT="text/html").status_code, 200)

    def test_swagger_for_staff(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/staff/tools/swagger/", HTTP_ACCEPT="text/html").status_code, 200)

    def test_suggestions_help_while_developing(self):
        result = self.gql("query { getTripLis { count } }")
        self.assertIn("Did you mean", result["errors"][0]["message"])
