# schema.py
import graphene
from graphql_jwt.decorators import login_required

# Models
from apps.tickets.models import Ticket
from apps.trip.models import Trip

# Types
from apps.tickets.types import TicketType, TicketPaginationType

# Libs
import graphene
from django.conf import settings
from graphql_jwt.decorators import login_required
from apps.default.methods.pagination import get_paginated_query


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
            return UpdateTicket(ok=False, ticket=None, error="Ticket not found")

        if trip_id:
            try:
                trip = Trip.objects.get(is_active=True, id=trip_id)
                ticket.trip = trip
            except Trip.DoesNotExist:
                return UpdateTicket(ok=False, ticket=None, error="Trip not found")

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
            if payment_method not in ["cash", "transfer"]:
                return UpdateTicket(ok=False, ticket=None, error="Invalid payment method")
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
            return CreateTicket(
                ok=False,
                ticket=None,
                error=str(e),
            )

        if payment_method not in ["cash", "transfer"]:
            return CreateTicket(
                ok=False,
                ticket=None,
                error="Invalid payment method",
            )

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
    def mutate(root, info, id):
        try:
            ticket = Ticket.objects.get(pk=id, is_active=True)
        except Ticket.DoesNotExist:
            raise Exception("Ticket not found or already deleted")

        ticket.delete()
        return DeleteTicket(success=True, message="Ticket deleted successfully")


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
        queryset = Ticket.objects.filter(is_active=True)
        result = get_paginated_query(queryset, page)
        return TicketPaginationType(
            results=result["results"],
            pages=result["pages"],
            count=result["count"],
            next=result["next"],
        )

    @login_required
    def resolve_get_ticket_by_id(root, info, id) -> Ticket:
        if len(id) == settings.SHORT_ID_SIZE:
            return Ticket.objects.get(
                is_active=True,
                id__startswith=id,
            )
        return Ticket.objects.get(is_active=True, id=id)

    @login_required
    def resolve_get_active_tickets(root, info):
        return Ticket.objects.filter(is_active=True)


schema = graphene.Schema(query=Query, mutation=Mutation)
