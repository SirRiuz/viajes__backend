# Libs
import graphene
from django.db.models import Prefetch
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

# Models
from app.models.ticket import Ticket
from app.models.trip import Trip

# Types
from app.types.ticket import TicketType, TicketPaginationType

# Utils
from app.utils.lookup import get_active_by_id
from app.utils.pagination import get_paginated_query

# Constants
from constants.exceptions import ValidationExceptions
from constants.models import PAYMENT_METHODS


def tickets_with_trip():
    """
    Tickets with their trip (and everything TripType reads) in a fixed number
    of queries. Prefetched rather than joined: the tickets query itself stays
    the same, and so does the order of the unordered lists.
    """
    return Ticket.objects.prefetch_related(Prefetch("trip", queryset=Trip.objects.with_details()))


class UpdateTicket(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)
        trip_id = graphene.String(required=False)
        client_name = graphene.String(required=False)
        client_id_number = graphene.String(required=False)
        client_email = graphene.String(required=False)
        client_phone = graphene.String(required=False)
        seat_number = graphene.String(required=True)
        payment_method = graphene.String(required=False)
        ticket_price = graphene.String(required=True)

    ok = graphene.Boolean()
    ticket = graphene.Field(TicketType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(
        root,
        info,
        id,
        trip_id=None,
        client_name=None,
        client_id_number=None,
        client_email=None,
        client_phone=None,
        seat_number=None,
        payment_method=None,
        ticket_price=None,
    ):
        try:
            ticket = Ticket.objects.get(is_active=True, id=id)
        except Ticket.DoesNotExist:
            return UpdateTicket(ok=False, ticket=None, error=ValidationExceptions.TICKET_NOT_FOUND)

        if trip_id:
            try:
                ticket.trip = Trip.objects.get(is_active=True, id=trip_id)
            except Trip.DoesNotExist:
                return UpdateTicket(ok=False, ticket=None, error=ValidationExceptions.TRIP_NOT_FOUND)

        if client_name is not None:
            ticket.client_name = client_name
        if client_id_number is not None:
            ticket.client_id_number = client_id_number
        if client_email is not None:
            ticket.client_email = client_email
        if client_phone is not None:
            ticket.client_phone = client_phone
        if seat_number is not None:
            ticket.seat_number = seat_number
        if payment_method is not None:
            if payment_method not in PAYMENT_METHODS:
                return UpdateTicket(ok=False, ticket=None, error=ValidationExceptions.INVALID_PAYMENT_METHOD)
            ticket.payment_method = payment_method
        if ticket_price is not None:
            ticket.ticket_price = ticket_price

        ticket.save()
        return UpdateTicket(ok=True, ticket=ticket, error=None)


class CreateTicket(graphene.Mutation):

    class Arguments:
        trip_id = graphene.String(required=True)
        client_name = graphene.String(required=True)
        client_id_number = graphene.String(required=True)
        client_email = graphene.String(required=False)
        client_phone = graphene.String(required=True)
        seat_number = graphene.Int(required=True)
        payment_method = graphene.String(required=True)
        ticket_price = graphene.String(required=True)

    ok = graphene.Boolean()
    ticket = graphene.Field(TicketType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(
        root,
        info,
        trip_id,
        client_name,
        client_id_number,
        client_email,
        client_phone,
        seat_number,
        payment_method,
        ticket_price,
    ):
        try:
            trip = Trip.objects.get(is_active=True, id=trip_id)
        except Exception as e:
            return CreateTicket(ok=False, ticket=None, error=str(e))

        if payment_method not in PAYMENT_METHODS:
            return CreateTicket(ok=False, ticket=None, error=ValidationExceptions.INVALID_PAYMENT_METHOD)

        ticket = Ticket.objects.create(
            trip=trip,
            client_name=client_name,
            client_id_number=client_id_number,
            client_email=client_email,
            client_phone=client_phone,
            seat_number=seat_number,
            payment_method=payment_method,
            ticket_price=ticket_price,
        )

        return CreateTicket(ok=True, ticket=ticket, error=None)


class DeleteTicket(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, id):
        try:
            ticket = Ticket.objects.get(pk=id, is_active=True)
        except Ticket.DoesNotExist:
            raise GraphQLError(ValidationExceptions.TICKET_NOT_FOUND_OR_DELETED)

        ticket.delete()
        return DeleteTicket(success=True, message=ValidationExceptions.TICKET_DELETED)


class Mutation(graphene.ObjectType):
    create_ticket = CreateTicket.Field()
    update_ticket = UpdateTicket.Field()
    delete_ticket = DeleteTicket.Field()


class Query(graphene.ObjectType):

    get_ticket_list = graphene.Field(
        TicketPaginationType,
        page=graphene.Int(required=False),
    )

    get_ticket_by_id = graphene.Field(
        TicketType,
        id=graphene.ID(required=True),
    )

    get_active_tickets = graphene.List(TicketType)

    @login_required
    def resolve_get_ticket_list(root, info, page=1):
        # Oldest first, as the rows came back before they had an explicit order
        queryset = tickets_with_trip().filter(is_active=True).order_by("create_at", "id")
        return TicketPaginationType(**get_paginated_query(queryset, page))

    @login_required
    def resolve_get_ticket_by_id(root, info, id) -> Ticket:
        return get_active_by_id(tickets_with_trip(), id)

    @login_required
    def resolve_get_active_tickets(root, info):
        return tickets_with_trip().filter(is_active=True)
