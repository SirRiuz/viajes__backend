from django.contrib.auth import get_user_model
from django.test import TestCase

from app.models.driver import Driver
from app.models.route import Route
from app.models.ticket import Ticket
from app.models.trip import Trip
from app.models.vessel import Vessel
from app.tests.helpers import make_ticket, make_trip
from honeypot.models.black_list import BlackList
from honeypot.models.login_attempt import LoginAttempt


class AdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("root", "r@example.com", "root-pass-123"))
        self.trip = make_trip()
        self.ticket = make_ticket(self.trip)

    def test_list_pages_show_the_short_id(self):
        for model, obj in [(Driver, self.trip.driver), (Route, self.trip.route), (Vessel, self.trip.vessel), (Trip, self.trip), (Ticket, self.ticket)]:
            response = self.client.get(f"/staff/tools/app/{model._meta.model_name}/")
            self.assertEqual(response.status_code, 200, model)
            self.assertContains(response, obj.id[:6])

    def test_user_and_honeypot_pages(self):
        BlackList.objects.create(ip_address="203.0.113.1")
        LoginAttempt.objects.create(username="bot", ip_address="203.0.113.1")
        for path in ("/staff/tools/app/user/", "/staff/tools/honeypot/blacklist/", "/staff/tools/honeypot/loginattempt/"):
            self.assertEqual(self.client.get(path).status_code, 200, path)


class StrTestCase(TestCase):
    def test_models_print_like_before(self):
        trip = make_trip()
        ticket = make_ticket(trip)
        self.assertEqual(str(trip.driver), "juan perez")
        self.assertEqual(str(trip.route), "sogamoso - tota")
        self.assertEqual(str(trip.vessel), trip.vessel.id)
        self.assertEqual(str(trip), trip.id)
        self.assertEqual(str(ticket), ticket.id)
        self.assertEqual(str(BlackList.objects.create(ip_address="203.0.113.1")), "203.0.113.1")
        self.assertEqual(str(LoginAttempt.objects.create(username="bot")), "bot")
