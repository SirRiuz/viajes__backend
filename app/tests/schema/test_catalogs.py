"""Drivers, routes, vessels and the current user."""

from app.models.driver import Driver
from app.models.route import Route
from app.models.vessel import Vessel
from app.tests.helpers import GraphQLTestCase, stamp
from app.tests.schema import documents as doc


class DriverTestCase(GraphQLTestCase):
    def test_driver_list_and_active_drivers(self):
        old = stamp(Driver.objects.create(full_name="juan perez", dni="1", license_id="L1"), 1)
        new = stamp(Driver.objects.create(full_name="maria lopez", dni="2"), 2)
        Driver.objects.filter(pk=new.pk).update(signature="drivers/signature/a.png")
        Driver.objects.create(full_name="retired", dni="3").disable()

        listing = self.gql(doc.DRIVER_LIST, {"page": 1})["data"]["getDriverList"]
        active = self.gql(doc.GET_ACTIVE_DRIVERS)["data"]["getActiveDrivers"]

        self.assertEqual((listing["count"], listing["pages"], listing["next"]), (2, 1, None))
        self.assertEqual([d["id"] for d in listing["results"]], [new.id, old.id])
        self.assertEqual(active[0]["fullName"], "Maria lopez")
        self.assertTrue(active[0]["signatureUrl"].endswith("/drivers/signature/a.png"))
        self.assertIsNone(active[0]["dniFileUrl"])
        self.assertEqual(active[1]["licenseId"], "L1")

    def test_create_update_delete_driver(self):
        created = self.gql(doc.CREATE_DRIVER, {"fullName": "nuevo", "dni": "5005", "licenseId": "L5"})["data"]["createDriver"]["driver"]
        driver_id = created["id"]
        self.assertEqual((created["fullName"], created["shortId"]), ("Nuevo", driver_id[:6]))

        updated = self.gql(doc.UPDATE_DRIVER, {"id": driver_id, "fullName": "editado", "dni": "5006", "licenseId": "L6"})
        self.assertEqual(updated["data"]["updateDriver"]["driver"]["dni"], "5006")

        self.assertEqual(self.gql(doc.DELETE_DRIVER, {"id": driver_id})["data"]["deleteDriver"], {"ok": True})
        self.assertFalse(Driver.objects.get(pk=driver_id).is_active)

        missing = self.gql(doc.UPDATE_DRIVER, {"id": driver_id, "fullName": "x", "dni": "x", "licenseId": "x"})
        self.assertEqual(missing["errors"][0]["message"], "Driver not found")

    def test_duplicate_dni_does_not_leak_sql(self):
        Driver.objects.create(full_name="a", dni="5005")
        result = self.gql(doc.CREATE_DRIVER, {"fullName": "b", "dni": "5005", "licenseId": "L"})
        self.assertEqual(result["errors"][0]["message"], "Something went wrong.")


class RouteTestCase(GraphQLTestCase):
    def test_route_crud(self):
        route = self.gql(doc.CREATE_ROUTE, {"routeName": "tota - aquitania"})["data"]["createRoute"]["route"]
        self.assertEqual(route["routeName"], "Tota - aquitania")

        updated = self.gql(doc.UPDATE_ROUTE, {"id": route["id"], "routeName": "otra"})["data"]["updateRoute"]["route"]
        self.assertEqual(updated["routeName"], "Otra")

        listing = self.gql(doc.ROUTE_LIST, {"page": 1})["data"]["getRouteList"]
        self.assertEqual(listing["results"], [{"id": route["id"], "shortId": route["id"][:6], "routeName": "Otra"}])

        self.assertEqual(self.gql(doc.DELETE_ROUTE, {"id": route["id"]})["data"]["deleteRoute"], {"success": True})
        self.assertEqual(self.gql(doc.GET_ACTIVE_ROUTES)["data"]["getActiveRoutes"], [])

    def test_route_errors(self):
        missing = self.gql(doc.UPDATE_ROUTE, {"id": "nope", "routeName": "x"})
        self.assertEqual(missing["errors"][0]["message"], "Route not found")
        query = "mutation { deleteRoute(id: \"nope\") { success message } }"
        self.assertEqual(self.gql(query)["data"]["deleteRoute"], {"success": False, "message": "Route not found"})


class VesselTestCase(GraphQLTestCase):
    def test_vessel_crud(self):
        self.assertEqual(self.gql(doc.CREATE_VESSEL, {"name": "lancha", "seatCount": 4})["data"]["createVessel"], {"ok": True})
        vessel = Vessel.objects.get()

        self.assertEqual(self.gql(doc.UPDATE_VESSEL, {"id": vessel.id, "name": "lancha 2", "seatCount": 6})["data"]["updateVessel"], {"ok": True})
        self.assertEqual(self.gql(doc.GET_ACTIVE_VESSELS)["data"]["getActiveVessels"], [{"id": vessel.id, "name": "Lancha 2", "seatCount": 6}])

        self.assertEqual(self.gql(doc.DELETE_VESSEL, {"id": vessel.id})["data"]["deleteVessel"], {"ok": True})
        self.assertEqual(self.gql(doc.DELETE_VESSEL, {"id": "nope"})["data"]["deleteVessel"], {"ok": False})

    def test_vessel_by_short_id(self):
        vessel = Vessel.objects.create(name="lancha", seat_count=3)
        query = "query($id: String!) { getVesselById(id: $id) { id seatCount } }"
        self.assertEqual(self.gql(query, {"id": vessel.id[:6]})["data"]["getVesselById"], {"id": vessel.id, "seatCount": 3})


class AccountTestCase(GraphQLTestCase):
    def test_token_auth_and_me(self):
        token = self.gql(doc.TOKEN_AUTH, {"username": "operador", "password": "op-pass-123"}, auth=False)["data"]["tokenAuth"]["token"]
        me = self.gql(doc.ME, token=token)["data"]["me"]

        self.assertEqual(me, {"id": self.user.id, "username": "Operador", "firstName": "", "lastName": "", "email": "op@example.com"})

    def test_me_anonymous_is_null(self):
        self.assertEqual(self.gql(doc.ME, auth=False), {"data": {"me": None}})

    def test_wrong_password(self):
        result = self.gql(doc.TOKEN_AUTH, {"username": "operador", "password": "nope"}, auth=False)
        self.assertEqual(result["errors"][0]["message"], "Please enter valid credentials")

    def test_routes_query_lists_newest_first(self):
        first = stamp(Route.objects.create(route_name="a"), 1)
        second = stamp(Route.objects.create(route_name="b"), 2)
        routes = self.gql(doc.GET_ACTIVE_ROUTES)["data"]["getActiveRoutes"]
        self.assertEqual([r["id"] for r in routes], [second.id, first.id])


class CatalogEdgeCasesTestCase(GraphQLTestCase):
    def test_delete_missing_driver(self):
        result = self.gql("mutation { deleteDriver(id: \"nope\") { ok error } }")
        self.assertEqual(result["data"]["deleteDriver"], {"ok": False, "error": "Driver not found"})

    def test_route_by_id(self):
        route = Route.objects.create(route_name="tota")
        query = "query($id: ID!) { getRouteById(id: $id) { id routeName } }"
        self.assertEqual(self.gql(query, {"id": route.id[:6]})["data"]["getRouteById"], {"id": route.id, "routeName": "Tota"})

    def test_create_vessel_with_invalid_seats(self):
        query = "mutation { createVessel(name: \"x\", seatCount: -1) { ok vessel { id } error } }"
        result = self.gql(query)["data"]["createVessel"]
        self.assertEqual((result["ok"], result["vessel"]), (False, None))
        self.assertTrue(result["error"])

    def test_update_missing_vessel(self):
        result = self.gql("mutation { updateVessel(id: \"nope\", name: \"x\") { ok error } }")
        self.assertEqual(result["data"]["updateVessel"], {"ok": False, "error": "Vessel not found"})

    def test_vessel_list_oldest_first(self):
        first = stamp(Vessel.objects.create(name="a", seat_count=1), 1)
        second = stamp(Vessel.objects.create(name="b", seat_count=1), 2)
        query = "query { getVesselList(page: 1) { count results { id shortId } } }"
        data = self.gql(query)["data"]["getVesselList"]
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"], [{"id": first.id, "shortId": first.id[:6]}, {"id": second.id, "shortId": second.id[:6]}])
