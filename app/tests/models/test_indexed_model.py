from unittest import mock

from django.db.models import Max
from django.test import TestCase

from app.models.ticket import Ticket
from app.models.trip import Trip
from app.tests.helpers import make_ticket, make_trip


class IndexedModelTestCase(TestCase):
    def test_indexes_are_sequential_per_model(self):
        trips = [make_trip(), make_trip()]
        tickets = [make_ticket(trips[0]), make_ticket(trips[1])]

        self.assertEqual([t.index for t in trips], [1, 2])
        self.assertEqual([t.index for t in tickets], [1, 2])

    def test_concurrent_sale_retries_with_the_next_number(self):
        trip = make_trip()
        make_ticket(trip)
        real_aggregate = Ticket.objects.aggregate
        # The first read is stale (another sale took number 1 meanwhile)
        stale_then_real = [{"index__max": 0}]

        def aggregate(*args, **kwargs):
            return stale_then_real.pop() if stale_then_real else real_aggregate(*args, **kwargs)

        with mock.patch.object(type(Ticket.objects), "aggregate", side_effect=aggregate):
            ticket = make_ticket(trip, seat=2)

        self.assertEqual(ticket.index, 2)
        self.assertEqual(Ticket.objects.aggregate(Max("index"))["index__max"], 2)

    def test_saving_again_keeps_the_index(self):
        trip = make_trip()
        trip.dispatcher = "otro"
        trip.save()
        trip.refresh_from_db()
        self.assertEqual((trip.index, Trip.objects.count()), (1, 1))

    def test_gives_up_after_the_retries(self):
        from django.db import IntegrityError, transaction

        trip = make_trip()
        make_ticket(trip)
        with mock.patch.object(type(Ticket.objects), "aggregate", return_value={"index__max": 0}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                make_ticket(trip, seat=2)
