import json
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from graphql_jwt.shortcuts import get_token

from app.models.driver import Driver
from app.models.route import Route
from app.models.ticket import Ticket
from app.models.trip import Trip
from app.models.vessel import Vessel

CLIENT_IP = "203.0.113.7"
BASE_TIME = datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc)


class GraphQLTestCase(TestCase):
    """HTTP calls to /graphql/ exactly as the frontend makes them."""

    def setUp(self):
        cache.clear()
        self.client = Client(HTTP_X_FORWARDED_FOR=CLIENT_IP)
        self.user = get_user_model().objects.create_user("operador", "op@example.com", "op-pass-123")
        self.token = get_token(self.user)

    def gql(self, query, variables=None, token=None, auth=True, **headers):
        if auth:
            headers["HTTP_AUTHORIZATION"] = f"JWT {token or self.token}"
        response = self.client.post(
            "/graphql/",
            data=json.dumps({"query": query, "variables": variables or {}}),
            content_type="application/json",
            **headers,
        )
        return json.loads(response.content)


def stamp(obj, hours):
    """Fixed creation time (auto_now_add can't be set on create)."""
    moment = BASE_TIME + timedelta(hours=hours)
    type(obj).objects.filter(pk=obj.pk).update(create_at=moment, update_at=moment)
    obj.refresh_from_db()
    return obj


def make_trip(seats=10, hours=0, tickets=0, inactive_tickets=0, **kwargs):
    """A trip with its driver, route and vessel, plus some tickets."""
    driver = kwargs.pop("driver", None) or Driver.objects.create(full_name="juan perez", dni=f"D{Driver.objects.count()}")
    route = kwargs.pop("route", None) or Route.objects.create(route_name="sogamoso - tota")
    vessel = kwargs.pop("vessel", None) or Vessel.objects.create(name="lancha uno", seat_count=seats)
    trip = stamp(Trip.objects.create(driver=driver, route=route, vessel=vessel, dispatcher="laura", **kwargs), hours)
    for n in range(tickets + inactive_tickets):
        ticket = make_ticket(trip, seat=n * 2 + 1, hours=hours + n / 10)
        if n >= tickets:
            ticket.disable()
    return trip


def make_ticket(trip, seat=1, hours=0, **kwargs):
    defaults = dict(
        client_name="cliente",
        client_id_number=f"CC{Ticket.objects.count()}",
        client_email="c@example.com",
        client_phone="3001234567",
        ticket_price="15000",
        payment_method="cash",
    )
    defaults.update(kwargs)
    return stamp(Ticket.objects.create(trip=trip, seat_number=seat, **defaults), hours)
