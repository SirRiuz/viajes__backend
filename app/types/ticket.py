# Python
from datetime import timezone, timedelta

# Libs
import graphene
from django.conf import settings
from graphene_django import DjangoObjectType

# Models
from app.models.ticket import Ticket

# Types
from app.types.pagination import pagination_type


BOGOTA_TZ = timezone(timedelta(hours=-5))


class TicketType(DjangoObjectType):

    short_id = graphene.String()
    create_at = graphene.String()
    create_at_time = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    def resolve_create_at_time(self, info):
        return self.create_at.astimezone(BOGOTA_TZ).strftime("%I:%M:%S %p")

    def resolve_create_at(self, info):
        return self.create_at.date()

    class Meta:
        model = Ticket
        fields = (
            "id",
            "index",
            "client_name",
            "client_id_number",
            "client_email",
            "client_phone",
            "seat_number",
            "payment_method",
            "ticket_price",
            "trip",
        )


TicketPaginationType = pagination_type("TicketPaginationType", TicketType)
