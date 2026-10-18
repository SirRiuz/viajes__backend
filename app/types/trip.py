# Libs
import graphene
from graphene_django import DjangoObjectType

# Django
from django.conf import settings

# Models
from app.models.trip import Trip

# Types
from app.types.pagination import pagination_type
from app.types.ticket import TicketType


class TripType(DjangoObjectType):

    passengers_counter = graphene.Int()
    passengers = graphene.List(TicketType)
    free_seats = graphene.List(graphene.Int)
    short_id = graphene.String()
    create_at = graphene.String()
    create_at_time = graphene.String()

    def resolve_create_at_time(self, info):
        return self.create_at.strftime("%I:%M:%S %p")

    def resolve_create_at(self, info):
        return self.create_at.date()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    # The three ticket fields share Trip.get_active_tickets(): prefetched by
    # Trip.objects.with_details(), or one query per trip otherwise.
    def resolve_free_seats(self, info):
        total_seats = list(range(1, self.vessel.seat_count + 1))
        occupied_seats = [ticket.seat_number for ticket in self.get_active_tickets()]
        return list(set(total_seats) - set(occupied_seats))

    def resolve_passengers(self, info):
        return self.get_active_tickets()

    def resolve_passengers_counter(self, info) -> int:
        return len(self.get_active_tickets())

    class Meta:
        model = Trip
        fields = (
            "id",
            "index",
            "create_at",
            "update_at",
            "driver",
            "route",
            "vessel",
            "dispatcher",
        )


TripPaginationType = pagination_type("TripPaginationType", TripType)
