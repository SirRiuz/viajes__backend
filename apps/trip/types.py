# Libs
import graphene
from graphene_django import DjangoObjectType

# Django
from django.conf import settings

# Models
from apps.trip.models import Trip
from apps.tickets.models import Ticket

# Types
from apps.route.types import RouteType
from apps.vessel.types import VesselType
from apps.driver.types import DriverType
from apps.tickets.types import TicketType


class TripType(DjangoObjectType):

    passengers_counter = graphene.Int()
    passengers = graphene.List(TicketType)
    free_seats = graphene.List(graphene.Int)
    short_id = graphene.String()
    create_at = graphene.String()

    def resolve_create_at(self, info):
        return self.create_at.date()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    def resolve_free_seats(self, info):
        total_seats = list(range(1, self.vessel.seat_count + 1))
        occupied_seats = Ticket.objects.filter(is_active=True, trip=self).values_list(
            "seat_number",
            flat=True,
        )

        available_seats = list(set(total_seats) - set(occupied_seats))
        return available_seats

    def resolve_passengers(self, info):
        return Ticket.objects.filter(is_active=True, trip=self).order_by("-create_at")

    def resolve_passengers_counter(self, info) -> int:
        return Ticket.objects.filter(is_active=True, trip=self).count()

    class Meta:
        model = Trip
        fields = (
            "id",
            "create_at",
            "update_at",
            "driver",
            "route",
            "vessel",
        )


class TripPaginationType(graphene.ObjectType):
    results = graphene.List(TripType)
    count = graphene.Int()
    pages = graphene.Int()
    next = graphene.Int()
