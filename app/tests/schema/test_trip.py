from django.db import connection
from django.test.utils import CaptureQueriesContext

from app.models.ticket import Ticket
from app.models.trip import Trip
from app.tests.helpers import GraphQLTestCase, make_ticket, make_trip
from app.tests.schema import documents as doc


class TripQueriesTestCase(GraphQLTestCase):
    def test_trip_list_answers_like_before(self):
        trip = make_trip(seats=6, hours=2, tickets=2, inactive_tickets=1)
        make_trip(hours=1)

        data = self.gql(doc.TRIP_LIST, {"page": 1})["data"]["getTripList"]

        self.assertEqual((data["count"], data["pages"], data["next"]), (2, 1, None))
        first = data["results"][0]
        self.assertEqual(first["id"], trip.id)
        self.assertEqual(first["shortId"], trip.id[:6])
        self.assertEqual(first["index"], trip.index)
        self.assertEqual(first["createAt"], "2026-01-05")
        # UTC clock, as the old resolver printed it
        self.assertEqual(first["createAtTime"], "03:00:00 PM")
        # Active tickets only, newest first
        self.assertEqual([p["seatNumber"] for p in first["passengers"]], [3, 1])
        self.assertEqual(first["vessel"], {"id": trip.vessel.id, "name": "Lancha uno", "seatCount": 6})
        self.assertEqual(first["driver"]["fullName"], "Juan perez")
        self.assertEqual(first["route"]["routeName"], "Sogamoso - tota")

    def test_trip_list_uses_a_fixed_number_of_queries(self):
        for hours in range(15):
            make_trip(hours=hours, tickets=3)

        self.client.get("/healthcheck/")  # loads the honeypot blacklist into the cache
        with CaptureQueriesContext(connection) as ctx:
            data = self.gql(doc.TRIP_LIST, {"page": 1})["data"]["getTripList"]

        self.assertEqual(len(data["results"]), 15)
        # user (JWT) + count + trips with joins + prefetched tickets
        self.assertLessEqual(len(ctx.captured_queries), 4)

    def test_trip_list_pages_and_order(self):
        trips = [make_trip(hours=h) for h in range(17)]

        page1 = self.gql(doc.TRIP_LIST, {"page": 1})["data"]["getTripList"]
        page2 = self.gql(doc.TRIP_LIST, {"page": 2})["data"]["getTripList"]
        oldest = self.gql(doc.TRIP_LIST, {"page": 1, "order": "oldest"})["data"]["getTripList"]
        beyond = self.gql(doc.TRIP_LIST, {"page": 9})["data"]["getTripList"]

        self.assertEqual((page1["count"], page1["pages"], page1["next"]), (17, 2, 2))
        self.assertEqual(page1["results"][0]["id"], trips[-1].id)
        self.assertEqual(len(page2["results"]), 2)
        self.assertIsNone(page2["next"])
        self.assertEqual(oldest["results"][0]["id"], trips[0].id)
        self.assertEqual((beyond["results"], beyond["next"]), ([], None))

    def test_trip_list_prefix_search(self):
        trip = make_trip(hours=1, tickets=2)
        make_ticket(trip, seat=9, client_id_number="CC777")
        other = make_trip(hours=2)

        def ids(prefix):
            results = self.gql(doc.TRIP_LIST, {"page": 1, "prefix": prefix})["data"]["getTripList"]["results"]
            return [t["id"] for t in results]

        self.assertEqual(ids("CC777"), [trip.id])
        self.assertEqual(ids(trip.id[:10]), [trip.id])
        self.assertEqual(ids("TOTA"), [other.id, trip.id])
        self.assertEqual(ids("zzz"), [])

    def test_trip_by_id_full_and_short(self):
        trip = make_trip(seats=5, tickets=2, inactive_tickets=1)

        full = self.gql(doc.GET_TRIP_BY_ID, {"id": trip.id})["data"]["getTripById"]
        short = self.gql(doc.GET_TRIP_BY_ID, {"id": trip.id[:6]})["data"]["getTripById"]

        self.assertEqual(full, short)
        self.assertEqual(full["passengersCounter"], 2)
        self.assertEqual(full["freeSeats"], [2, 4, 5])
        # Bogotá clock on tickets (UTC-5)
        self.assertEqual(full["passengers"][0]["createAtTime"], "08:06:00 AM")

    def test_free_seats_query(self):
        trip = make_trip(seats=4, tickets=1)
        data = self.gql(doc.GET_FREE_SEATS, {"id": trip.id})["data"]["getTripById"]
        self.assertEqual(data["freeSeats"], [2, 3, 4])

    def test_missing_trip_keeps_django_message(self):
        result = self.gql(doc.GET_TRIP_BY_ID, {"id": "f" * 64})
        self.assertEqual(result["errors"][0]["message"], "Trip matching query does not exist.")


class TripMutationsTestCase(GraphQLTestCase):
    def setUp(self):
        super().setUp()
        self.trip = make_trip()

    def ids(self):
        return {"driverId": self.trip.driver.id, "routeId": self.trip.route.id, "vesselId": self.trip.vessel.id}

    def test_create_trip_numbers_trips(self):
        result = self.gql(doc.CREATE_TRIP, {**self.ids(), "dispatcher": "carlos"})

        self.assertEqual(result["data"]["createTrip"], {"ok": True})
        self.assertEqual(Trip.objects.latest("index").index, self.trip.index + 1)

    def test_create_trip_with_missing_driver(self):
        query = "mutation($d: String!, $r: String!, $v: String!) { createTrip(driverId: $d, routeId: $r, vesselId: $v, dispatcher: \"x\") { ok error } }"
        result = self.gql(query, {"d": "nope", "r": self.trip.route.id, "v": self.trip.vessel.id})
        self.assertEqual(result["data"]["createTrip"], {"ok": False, "error": "Driver matching query does not exist."})

    def test_update_trip(self):
        result = self.gql(doc.UPDATE_TRIP, {"id": self.trip.id, **self.ids(), "dispatcher": "carlos"})

        self.assertEqual(result["data"]["updateTrip"], {"ok": True})
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.dispatcher, "carlos")

    def test_update_trip_without_dispatcher_keeps_legacy_behaviour(self):
        # Known legacy quirk, kept on purpose: an omitted dispatcher is saved
        # as «False». The frontend always sends it.
        self.gql("mutation($id: String!) { updateTrip(id: $id) { ok } }", {"id": self.trip.id})
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.dispatcher, "False")

    def test_delete_trip_removes_it_and_its_tickets(self):
        make_ticket(self.trip)

        result = self.gql(doc.DELETE_TRIP, {"id": self.trip.id})
        again = self.gql(doc.DELETE_TRIP, {"id": self.trip.id})

        self.assertEqual(result["data"]["deleteTrip"], {"success": True})
        self.assertFalse(Trip.objects.filter(pk=self.trip.pk).exists())
        self.assertFalse(Ticket.objects.exists())
        self.assertEqual(again["errors"][0]["message"], "Trip not found or already deleted")


class TripEdgeCasesTestCase(GraphQLTestCase):
    QUERY = "mutation($id: String!, $d: String, $r: String, $v: String) { updateTrip(id: $id, driverId: $d, routeId: $r, vesselId: $v, dispatcher: \"x\") { ok error } }"

    def test_update_trip_errors(self):
        trip = make_trip()
        cases = [
            ({"id": "nope"}, "Trip not found"),
            ({"id": trip.id, "d": "nope"}, "Driver not found"),
            ({"id": trip.id, "r": "nope"}, "Route not found"),
            ({"id": trip.id, "v": "nope"}, "Vessel not found"),
        ]
        for variables, error in cases:
            self.assertEqual(self.gql(self.QUERY, variables)["data"]["updateTrip"], {"ok": False, "error": error})

    def test_recent_trips(self):
        trips = [make_trip(hours=h, tickets=1) for h in range(12)]
        data = self.gql("query { getRecentTrips { id passengersCounter } }")["data"]["getRecentTrips"]
        self.assertEqual([t["id"] for t in data], [t.id for t in reversed(trips)][:10])
        self.assertEqual({t["passengersCounter"] for t in data}, {1})

    def test_active_tickets_without_prefetch(self):
        trip = make_trip(tickets=2, inactive_tickets=1)
        fresh = Trip.objects.get(pk=trip.pk)
        self.assertEqual([t.seat_number for t in fresh.get_active_tickets()], [3, 1])
