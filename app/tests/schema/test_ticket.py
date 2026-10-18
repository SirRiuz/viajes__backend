from django.db import connection
from django.test.utils import CaptureQueriesContext

from app.models.ticket import Ticket
from app.tests.helpers import GraphQLTestCase, make_ticket, make_trip
from app.tests.schema import documents as doc

TICKET_LIST = "query($page: Int) { getTicketList(page: $page) { count pages next results { id seatNumber trip { id passengersCounter freeSeats vessel { name } } } } }"


class TicketMutationsTestCase(GraphQLTestCase):
    def setUp(self):
        super().setUp()
        self.trip = make_trip(seats=4)

    def ticket_vars(self, **overrides):
        values = {
            "clientEmail": "x@example.com",
            "clientIdNumber": "CC9",
            "clientName": "pasajero",
            "clientPhone": "3001",
            "paymentMethod": "cash",
            "seatNumber": 2,
            "ticketPrice": "20000",
            "tripId": self.trip.id,
        }
        values.update(overrides)
        return values

    def test_create_ticket_numbers_tickets(self):
        first = self.gql(doc.CREATE_TICKET, self.ticket_vars())
        second = self.gql(doc.CREATE_TICKET, self.ticket_vars(seatNumber=3))

        self.assertEqual(first["data"]["createTicket"], {"ok": True, "error": None})
        self.assertEqual(second["data"]["createTicket"], {"ok": True, "error": None})
        self.assertEqual(sorted(Ticket.objects.values_list("index", flat=True)), [1, 2])

    def test_create_ticket_rejects_unknown_payment_method(self):
        result = self.gql(doc.CREATE_TICKET, self.ticket_vars(paymentMethod="card"))
        self.assertEqual(result["data"]["createTicket"], {"ok": False, "error": "Invalid payment method"})
        self.assertFalse(Ticket.objects.exists())

    def test_create_ticket_on_missing_trip(self):
        result = self.gql(doc.CREATE_TICKET, self.ticket_vars(tripId="nope"))
        self.assertEqual(result["data"]["createTicket"], {"ok": False, "error": "Trip matching query does not exist."})

    def test_update_ticket(self):
        ticket = make_ticket(self.trip)

        result = self.gql(doc.UPDATE_TICKET, {"id": ticket.id, "seatNumber": "3", "ticketPrice": "25000", "paymentMethod": "transfer"})

        self.assertEqual(result["data"]["updateTicket"], {"ok": True})
        ticket.refresh_from_db()
        self.assertEqual((ticket.seat_number, ticket.ticket_price, ticket.payment_method), (3, "25000", "transfer"))

    def test_update_ticket_errors(self):
        ticket = make_ticket(self.trip)
        query = "mutation($id: String!, $m: String, $t: String) { updateTicket(id: $id, seatNumber: \"1\", ticketPrice: \"1\", paymentMethod: $m, tripId: $t) { ok error } }"

        self.assertEqual(self.gql(query, {"id": "nope"})["data"]["updateTicket"], {"ok": False, "error": "Ticket not found"})
        self.assertEqual(self.gql(query, {"id": ticket.id, "m": "card"})["data"]["updateTicket"], {"ok": False, "error": "Invalid payment method"})
        self.assertEqual(self.gql(query, {"id": ticket.id, "t": "nope"})["data"]["updateTicket"], {"ok": False, "error": "Trip not found"})

    def test_delete_ticket(self):
        ticket = make_ticket(self.trip)

        result = self.gql(doc.DELETE_TICKET, {"id": ticket.id})
        again = self.gql(doc.DELETE_TICKET, {"id": ticket.id})

        self.assertEqual(result["data"]["deleteTicket"], {"success": True})
        self.assertEqual(again["errors"][0]["message"], "Ticket not found or already deleted")


class TicketQueriesTestCase(GraphQLTestCase):
    def test_ticket_list_with_trip_in_fixed_queries(self):
        for hours in range(5):
            make_trip(hours=hours, tickets=3)

        self.client.get("/healthcheck/")  # loads the honeypot blacklist into the cache
        with CaptureQueriesContext(connection) as ctx:
            data = self.gql(TICKET_LIST, {"page": 1})["data"]["getTicketList"]

        self.assertEqual((data["count"], len(data["results"])), (15, 15))
        self.assertEqual(data["results"][0]["trip"]["passengersCounter"], 3)
        # user + count + tickets + trips with joins + their tickets
        self.assertLessEqual(len(ctx.captured_queries), 5)

    def test_ticket_by_short_id(self):
        ticket = make_ticket(make_trip())
        query = "query($id: ID!) { getTicketById(id: $id) { id paymentMethod } }"
        data = self.gql(query, {"id": ticket.id[:6]})["data"]["getTicketById"]
        self.assertEqual(data, {"id": ticket.id, "paymentMethod": "CASH"})


class TicketEdgeCasesTestCase(GraphQLTestCase):
    def test_update_every_client_field(self):
        trip = make_trip()
        ticket = make_ticket(trip)
        query = """mutation($id: String!) { updateTicket(id: $id, seatNumber: "4", ticketPrice: "9",
            clientName: "ana", clientIdNumber: "CC1", clientEmail: "a@example.com", clientPhone: "300") { ok } }"""

        self.assertEqual(self.gql(query, {"id": ticket.id})["data"]["updateTicket"], {"ok": True})
        ticket.refresh_from_db()
        self.assertEqual(
            (ticket.client_name, ticket.client_id_number, ticket.client_email, ticket.client_phone),
            ("ana", "CC1", "a@example.com", "300"),
        )

    def test_active_tickets(self):
        trip = make_trip(tickets=2, inactive_tickets=1)
        data = self.gql("query { getActiveTickets { seatNumber trip { id } } }")["data"]["getActiveTickets"]
        self.assertEqual(sorted(t["seatNumber"] for t in data), [1, 3])
        self.assertEqual({t["trip"]["id"] for t in data}, {trip.id})

    def test_ticket_list_oldest_first(self):
        trip = make_trip()
        tickets = [make_ticket(trip, seat=n, hours=n) for n in range(3)]
        data = self.gql(TICKET_LIST, {"page": 1})["data"]["getTicketList"]
        self.assertEqual([t["id"] for t in data["results"]], [t.id for t in tickets])
