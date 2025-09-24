# Libs
import graphene
from django.conf import settings
from graphene_django import DjangoObjectType

# Models
from apps.tickets.models import Ticket

# Types
from apps.trip.types import Trip


class TicketType(DjangoObjectType):

    short_id = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    class Meta:
        model = Ticket
        fields = (
            "id",
            "created_at",
            "updated_at",
            "client_name",
            "client_id_number",
            "client_email",
            "client_phone",
            "seat_number",
            "payment_method",
            "ticket_price",
            "trip",
        )


class TicketPaginationType(graphene.ObjectType):
    results = graphene.List(TicketType)
    count = graphene.Int()
    pages = graphene.Int()
    next = graphene.Int()
