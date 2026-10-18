# Libs
import graphene
from django.db.models import Q
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

# Models
from app.models.driver import Driver
from app.models.route import Route
from app.models.trip import Trip
from app.models.vessel import Vessel

# Types
from app.types.trip import TripType, TripPaginationType

# Utils
from app.utils.lookup import get_active_by_id
from app.utils.pagination import get_paginated_query

# Constants
from constants.exceptions import ValidationExceptions


class CreateTrip(graphene.Mutation):

    class Arguments:
        driver_id = graphene.String(required=True)
        route_id = graphene.String(required=True)
        vessel_id = graphene.String(required=True)
        dispatcher = graphene.String(required=True)

    ok = graphene.Boolean()
    trip = graphene.Field(TripType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(
        root,
        info,
        driver_id,
        route_id,
        vessel_id,
        dispatcher,
    ):
        try:
            driver = Driver.objects.get(is_active=True, id=driver_id)
            vessel = Vessel.objects.get(is_active=True, id=vessel_id)
            route = Route.objects.get(is_active=True, id=route_id)
        except Exception as e:
            return CreateTrip(ok=False, error=str(e))

        trip = Trip.objects.create(
            dispatcher=dispatcher,
            driver=driver,
            vessel=vessel,
            route=route,
        )

        return CreateTrip(ok=True, trip=trip, error=None)


class DeleteTrip(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, id):
        try:
            trip = Trip.objects.get(pk=id, is_active=True)
        except Trip.DoesNotExist:
            raise GraphQLError(ValidationExceptions.TRIP_NOT_FOUND_OR_DELETED)

        trip.delete()
        return DeleteTrip(success=True, message=ValidationExceptions.TRIP_DELETED)


class UpdateTrip(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)
        driver_id = graphene.String(required=False)
        route_id = graphene.String(required=False)
        vessel_id = graphene.String(required=False)
        dispatcher = graphene.String(required=False)

    ok = graphene.Boolean()
    trip = graphene.Field(TripType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(
        root,
        info,
        id,
        driver_id=None,
        route_id=None,
        vessel_id=None,
        dispatcher=False,
    ):
        try:
            trip = Trip.objects.get(pk=id, is_active=True)
        except Trip.DoesNotExist:
            return UpdateTrip(ok=False, trip=None, error=ValidationExceptions.TRIP_NOT_FOUND)

        if driver_id is not None:
            try:
                trip.driver = Driver.objects.get(is_active=True, id=driver_id)
            except Driver.DoesNotExist:
                return UpdateTrip(ok=False, trip=None, error=ValidationExceptions.DRIVER_NOT_FOUND)

        if route_id is not None:
            try:
                trip.route = Route.objects.get(is_active=True, id=route_id)
            except Route.DoesNotExist:
                return UpdateTrip(ok=False, trip=None, error=ValidationExceptions.ROUTE_NOT_FOUND)

        if vessel_id is not None:
            try:
                trip.vessel = Vessel.objects.get(is_active=True, id=vessel_id)
            except Vessel.DoesNotExist:
                return UpdateTrip(ok=False, trip=None, error=ValidationExceptions.VESSEL_NOT_FOUND)

        if dispatcher is not None:
            trip.dispatcher = dispatcher

        trip.save()
        return UpdateTrip(ok=True, trip=trip, error=None)


class Mutation(graphene.ObjectType):
    create_trip = CreateTrip.Field()
    update_trip = UpdateTrip.Field()
    delete_trip = DeleteTrip.Field()


class Query(graphene.ObjectType):

    get_trip_by_id = graphene.Field(
        TripType,
        id=graphene.String(required=True),
    )

    get_recent_trips = graphene.List(TripType)

    get_trip_list = graphene.Field(
        TripPaginationType,
        page=graphene.Int(required=False),
        prefix=graphene.String(required=False),
        order=graphene.String(required=False),
    )

    @login_required
    def resolve_get_trip_by_id(root, info, id) -> Trip:
        return get_active_by_id(Trip.objects.with_details(), id)

    @login_required
    def resolve_get_recent_trips(root, info):
        return Trip.objects.with_details().filter(is_active=True).order_by("-create_at")[:10]

    @login_required
    def resolve_get_trip_list(
        root,
        info,
        page=1,
        prefix=None,
        order=None,
    ):
        queryset = Trip.objects.with_details().filter(is_active=True)

        if prefix:
            queryset = queryset.filter(
                Q(driver__full_name__icontains=prefix)
                | Q(id__icontains=prefix)
                | Q(route__route_name__icontains=prefix)
                | Q(vessel__name__icontains=prefix)
                | Q(ticket__client_id_number__icontains=prefix)
            ).distinct()

        queryset = queryset.order_by("create_at" if order == "oldest" else "-create_at")
        return TripPaginationType(**get_paginated_query(queryset, page))
