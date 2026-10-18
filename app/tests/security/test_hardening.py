import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, override_settings

from app.models.driver import Driver
from app.models.route import Route
from app.schemas.account import LOGIN_MAX_FAILURES
from app.middlewares.admin_throttle import MAX_ATTEMPTS
from app.tests.helpers import CLIENT_IP, GraphQLTestCase, make_ticket, make_trip
from app.tests.schema import documents as doc
from app.utils.graphql_limits import MAX_ALIASES, MAX_DEPTH
from viajes.schema import schema

PERMISSION_DENIED = "You do not have permission to perform this action"
LOCAL_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class AuthenticationRequiredTestCase(GraphQLTestCase):
    """Every operation but tokenAuth/verifyToken/refreshToken/me needs a session."""

    PUBLIC = {"tokenAuth", "verifyToken", "refreshToken", "me"}

    def test_every_mutation_rejects_anonymous_calls(self):
        trip = make_trip()
        ticket = make_ticket(trip)
        ids = {"id": trip.id, "tripId": trip.id, "driverId": trip.driver.id, "routeId": trip.route.id, "vesselId": trip.vessel.id}
        calls = [
            (doc.CREATE_DRIVER, {"fullName": "x", "dni": "9", "licenseId": "x"}),
            (doc.UPDATE_DRIVER, {"id": trip.driver.id, "fullName": "x", "dni": "9", "licenseId": "x"}),
            (doc.DELETE_DRIVER, {"id": trip.driver.id}),
            (doc.CREATE_ROUTE, {"routeName": "x"}),
            (doc.UPDATE_ROUTE, {"id": trip.route.id, "routeName": "x"}),
            (doc.DELETE_ROUTE, {"id": trip.route.id}),
            (doc.CREATE_VESSEL, {"name": "x", "seatCount": 1}),
            (doc.UPDATE_VESSEL, {"id": trip.vessel.id, "name": "x", "seatCount": 1}),
            (doc.DELETE_VESSEL, {"id": trip.vessel.id}),
            (doc.CREATE_TRIP, {**ids, "dispatcher": "x"}),
            (doc.UPDATE_TRIP, {**ids, "dispatcher": "x"}),
            (doc.DELETE_TRIP, {"id": trip.id}),
            (doc.CREATE_TICKET, {"clientIdNumber": "1", "clientName": "x", "clientPhone": "1", "paymentMethod": "cash", "seatNumber": 2, "ticketPrice": "1", "tripId": trip.id}),
            (doc.UPDATE_TICKET, {"id": ticket.id, "seatNumber": "1", "ticketPrice": "1"}),
            (doc.DELETE_TICKET, {"id": ticket.id}),
        ]
        covered = set()
        for query, variables in calls:
            result = self.gql(query, variables, auth=False)
            field = next(iter(result["data"]))
            covered.add(field)
            self.assertIsNone(result["data"][field], field)
            self.assertEqual(result["errors"][0]["message"], PERMISSION_DENIED, field)

        all_mutations = set(schema.graphql_schema.mutation_type.fields)
        self.assertEqual(all_mutations - covered, self.PUBLIC & all_mutations)
        # Nothing was written
        self.assertEqual(Route.objects.filter(is_active=True).count(), 1)
        self.assertTrue(type(trip).objects.filter(pk=trip.pk).exists())

    def test_every_query_rejects_anonymous_calls(self):
        for field in set(schema.graphql_schema.query_type.fields) - self.PUBLIC:
            args = schema.graphql_schema.query_type.fields[field].args
            arguments = "(id: \"x\")" if "id" in args else ""
            result = self.gql("query { %s%s { __typename } }" % (field, arguments), auth=False)
            self.assertEqual(result["errors"][0]["message"], PERMISSION_DENIED, field)


@override_settings(STORAGES=LOCAL_STORAGE)
class DriverDocumentsUploadTestCase(GraphQLTestCase):
    def setUp(self):
        super().setUp()
        self.driver = Driver.objects.create(full_name="juan", dni="1")
        self.url = f"/drivers/{self.driver.id}/upload-documents/"

    def upload(self, **headers):
        pdf = SimpleUploadedFile("dni.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        return self.client.post(self.url, {"dni_pdf": pdf}, **headers)

    def test_anonymous_upload_is_refused(self):
        response = self.upload()
        self.assertEqual(response.status_code, 401)
        self.driver.refresh_from_db()
        self.assertFalse(self.driver.dni_pdf)

    def test_bad_token_is_refused(self):
        self.assertEqual(self.upload(HTTP_AUTHORIZATION="JWT nope").status_code, 401)

    def test_upload_with_the_frontend_token(self):
        response = self.upload(HTTP_AUTHORIZATION=f"JWT {self.token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.driver.id)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.dni_pdf.name.startswith("drivers/dni/dni"))

    def test_missing_driver(self):
        response = self.client.post("/drivers/nope/upload-documents/", HTTP_AUTHORIZATION=f"JWT {self.token}")
        self.assertEqual((response.status_code, response.json()), (404, {"error": "Driver not found"}))


@override_settings(DEBUG=True)
class GraphQLLimitsTestCase(GraphQLTestCase):
    """Which limit refused the query (the real messages exist only with DEBUG)."""

    def test_too_many_aliases(self):
        aliases = " ".join(f"a{i}: me {{ id }}" for i in range(MAX_ALIASES + 1))
        result = self.gql("query { %s }" % aliases)
        self.assertEqual(result["errors"][0]["message"], f"Too many aliases (max {MAX_ALIASES}).")

    def test_too_deep(self):
        nested = "trip { " * MAX_DEPTH + "id" + " }" * MAX_DEPTH
        result = self.gql("query { getActiveTickets { %s } }" % nested)
        self.assertEqual(result["errors"][0]["message"], f"Query too deep (max {MAX_DEPTH}).")

    def test_oversized_document(self):
        result = self.gql("query { me { id } }" + " " * 13_000)
        self.assertEqual(result["errors"][0]["message"], "Query too large.")

    def test_syntax_error(self):
        result = self.gql("query { me { id }")
        self.assertIn("Syntax Error", result["errors"][0]["message"])

    def test_mutations_need_post(self):
        response = self.client.get("/graphql/", {"query": "mutation { deleteRoute(id: \"x\") { success } }"})
        self.assertEqual(response.status_code, 405)

    def test_documents_are_parsed_once(self):
        from app.views import graphql as view_module

        with mock.patch.object(view_module, "parse", wraps=view_module.parse) as parse:
            query = "query { me { id username } }"
            first = self.gql(query)
            second = self.gql(query)

        self.assertEqual(first, second)
        self.assertEqual(first["data"]["me"]["username"], "Operador")
        self.assertLessEqual(parse.call_count, 1)


class GraphQLProductionErrorsTestCase(GraphQLTestCase):
    """In production every refusal reads the same: nothing names the engine."""

    def test_rejected_queries_share_one_generic_message(self):
        queries = {
            "introspection": "{ __schema { queryType { name } } }",
            "aliases": "query { %s }" % " ".join(f"a{i}: me {{ id }}" for i in range(MAX_ALIASES + 1)),
            "depth": "query { getActiveTickets { %s } }" % ("trip { " * MAX_DEPTH + "id" + " }" * MAX_DEPTH),
            "size": "query { me { id } }" + " " * 13_000,
            "syntax": "query { me { id }",
            "unknown field": "query { getTripLis { count } }",
            "bad variable": "query($p: Int) { getTripList(page: $p) { count } }",
        }
        for name, query in queries.items():
            variables = {"p": "uno"} if name == "bad variable" else None
            result = self.gql(query, variables)
            self.assertIsNone(result.get("data"), name)
            self.assertTrue(result["errors"], name)
            self.assertEqual({e["message"] for e in result["errors"]}, {"Invalid query."}, name)
            self.assertEqual({k for e in result["errors"] for k in e}, {"message"}, name)

    def test_missing_query_string(self):
        response = self.client.post("/graphql/", data="{}", content_type="application/json")
        self.assertEqual((response.status_code, json.loads(response.content)), (400, {"errors": [{"message": "Invalid query."}]}))

    def test_resolver_messages_the_frontend_reads_are_kept(self):
        self.assertEqual(self.gql("query { getDriverById(id: \"nope\") { id } }")["errors"][0]["message"], "Driver matching query does not exist.")
        denied = self.gql("query { getTripList { count } }", auth=False)
        self.assertEqual(denied["errors"][0]["message"], "You do not have permission to perform this action")


class LoginThrottleTestCase(GraphQLTestCase):
    def login(self, password, ip=CLIENT_IP):
        return self.gql(doc.TOKEN_AUTH, {"username": "operador", "password": password}, auth=False, HTTP_X_FORWARDED_FOR=ip)

    def test_failed_logins_are_capped_per_address(self):
        for _ in range(LOGIN_MAX_FAILURES):
            self.assertEqual(self.login("nope")["errors"][0]["message"], "Please enter valid credentials")

        blocked = self.login("op-pass-123")
        self.assertEqual(blocked["errors"][0]["message"], "Too many attempts. Try again later.")
        # Another address is not affected
        self.assertTrue(self.login("op-pass-123", ip="198.51.100.1")["data"]["tokenAuth"]["token"])

    def test_successful_logins_are_not_counted(self):
        for _ in range(LOGIN_MAX_FAILURES + 2):
            self.assertTrue(self.login("op-pass-123")["data"]["tokenAuth"]["token"])

    def test_admin_login_is_capped(self):
        client = Client(HTTP_X_FORWARDED_FOR=CLIENT_IP)
        for _ in range(MAX_ATTEMPTS):
            self.assertNotEqual(client.post("/staff/tools/login/", {"username": "x", "password": "y"}).status_code, 429)
        self.assertEqual(client.post("/staff/tools/login/", {"username": "x", "password": "y"}).status_code, 429)


class ErrorMaskingTestCase(GraphQLTestCase):
    def test_public_errors_reach_the_client(self):
        result = self.gql("query { getDriverById(id: \"nope\") { id } }")
        self.assertEqual(result["errors"][0]["message"], "Driver matching query does not exist.")

    @override_settings(DEBUG=True)
    def test_debug_shows_internal_errors(self):
        Driver.objects.create(full_name="a", dni="1")
        result = self.gql(doc.CREATE_DRIVER, {"fullName": "b", "dni": "1", "licenseId": "L"})
        self.assertNotEqual(result["errors"][0]["message"], "Something went wrong.")


class HealthcheckTestCase(GraphQLTestCase):
    def test_healthcheck(self):
        response = self.client.get("/healthcheck/")
        self.assertEqual((response.status_code, json.loads(response.content)), (200, "ok"))


@override_settings(DEBUG=True)
class QueryShapeTestCase(GraphQLTestCase):
    def test_too_many_fields(self):
        result = self.gql("query { me { %s } }" % " ".join(["id"] * 300))
        self.assertEqual(result["errors"][0]["message"], "Query too large (max 300 fields).")

    def test_huge_documents_stop_being_walked(self):
        result = self.gql("query { me { %s } }" % " ".join(["id"] * 700))
        self.assertEqual(result["errors"][0]["message"], "Query too large (max 300 fields).")

    def test_fragments_count_towards_the_shape(self):
        query = """
            query { me { ...A ...Missing } }
            fragment A on UserType { id ... on UserType { email } ...B }
            fragment B on UserType { username ...A }
        """
        messages = [e["message"] for e in self.gql(query)["errors"]]
        self.assertTrue(any("Cannot spread fragment" in m or "Unknown fragment" in m for m in messages))

    def test_valid_fragments_resolve(self):
        query = "query { me { ...A } } fragment A on UserType { id ... on UserType { email } }"
        self.assertEqual(self.gql(query)["data"]["me"]["email"], "op@example.com")


class GraphQLViewTestCase(GraphQLTestCase):
    def view(self, request, **kwargs):
        from app.views.graphql import ProtectedGraphQLView

        request.user = self.user
        return ProtectedGraphQLView.as_view(**kwargs)(request)

    @override_settings(DEBUG=True)
    def test_missing_query(self):
        response = self.client.post("/graphql/", data="{}", content_type="application/json")
        self.assertEqual((response.status_code, json.loads(response.content)["errors"][0]["message"]), (400, "Must provide query string."))

    def test_get_mutation_while_showing_graphiql(self):
        from app.views.graphql import ProtectedGraphQLView

        request = RequestFactory().get("/graphiql/")
        query = "mutation { deleteRoute(id: \"x\") { success } }"
        result = ProtectedGraphQLView(graphiql=True).execute_graphql_request(request, {}, query, None, None, show_graphiql=True)
        self.assertIsNone(result)

    def test_custom_execution_context(self):
        from graphql import ExecutionContext

        request = RequestFactory().post("/graphql/", json.dumps({"query": "query { me { id } }"}), content_type="application/json")
        response = self.view(request, execution_context_class=ExecutionContext)
        self.assertEqual(json.loads(response.content), {"data": {"me": {"id": self.user.id}}})

    def test_atomic_mutations_roll_back_on_error_flag(self):
        from graphene_django.constants import MUTATION_ERRORS_FLAG
        from graphene_django.settings import graphene_settings

        body = json.dumps({"query": "mutation { createRoute(routeName: \"x\") { route { id } } }"})
        request = RequestFactory().post("/graphql/", body, content_type="application/json", HTTP_AUTHORIZATION=f"JWT {self.token}")
        setattr(request, MUTATION_ERRORS_FLAG, True)
        with mock.patch.object(graphene_settings, "ATOMIC_MUTATIONS", True):
            self.view(request)
        self.assertFalse(Route.objects.filter(route_name="x").exists())

    def test_unexpected_errors_are_masked(self):
        from app.views import graphql as view_module

        with mock.patch.object(view_module, "execute", side_effect=RuntimeError("secret detail")):
            result = self.gql("query { me { id } }")
        self.assertEqual(result["errors"], [{"message": "Something went wrong."}])


class UploadEdgeCasesTestCase(GraphQLTestCase):
    def test_token_of_a_deleted_user(self):
        driver = Driver.objects.create(full_name="juan", dni="1")
        self.user.delete()
        response = self.client.post(f"/drivers/{driver.id}/upload-documents/", HTTP_AUTHORIZATION=f"JWT {self.token}")
        self.assertEqual(response.status_code, 401)

    def test_invalid_file(self):
        driver = Driver.objects.create(full_name="juan", dni="1")
        response = self.client.post(
            f"/drivers/{driver.id}/upload-documents/", {"dni_pdf": "not a file"}, HTTP_AUTHORIZATION=f"JWT {self.token}"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("dni_pdf", response.json())
