# Libs
import graphene
from django.conf import settings
from graphql_jwt.decorators import login_required
from apps.trip.types import TripType, TripPaginationType
from apps.default.methods.pagination import get_paginated_query

# Models
from apps.trip.models import Trip
from apps.driver.models import Driver
from apps.vessel.models import Vessel
from apps.route.models import Route


class CreateTrip(graphene.Mutation):

    class Arguments:
        driver_id = graphene.String(required=True)
        route_id = graphene.String(required=True)
        vessel_id = graphene.String(required=True)

    ok = graphene.Boolean()
    trip = graphene.Field(TripType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, driver_id, route_id, vessel_id):
        try:
            driver = Driver.objects.get(is_active=True, id=driver_id)
            route = Route.objects.get(is_active=True, id=route_id)
            vessel = Vessel.objects.get(is_active=True, id=vessel_id)
        except Exception as e:
            return CreateTrip(
                ok=False,
                trip=None,
                error=str(e),
            )

        trip = Trip.objects.create(
            driver=driver,
            route=route,
            vessel=vessel,
        )
        return CreateTrip(ok=True, trip=trip, error=None)


class DeleteTrip(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    def mutate(root, info, id):
        try:
            trip = Trip.objects.get(pk=id, is_active=True)
        except Trip.DoesNotExist:
            raise Exception("Trip not found or already deleted")

        trip.is_active = False
        trip.save()

        return DeleteTrip(success=True, message="Trip deleted successfully")


class UpdateTrip(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)
        driver_id = graphene.String(required=False)
        route_id = graphene.String(required=False)
        vessel_id = graphene.String(required=False)

    ok = graphene.Boolean()
    trip = graphene.Field(TripType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, id, driver_id=None, route_id=None, vessel_id=None):
        try:
            trip = Trip.objects.get(pk=id, is_active=True)
        except Trip.DoesNotExist:
            return UpdateTrip(ok=False, trip=None, error="Trip not found")

        if driver_id is not None:
            print("driver_iddriver_iddriver_iddriver_iddriver_iddriver_iddriver_iddriver_id")
            try:
                driver = Driver.objects.get(is_active=True, id=driver_id)
                trip.driver = driver
            except Driver.DoesNotExist:
                return UpdateTrip(ok=False, trip=None, error="Driver not found")

        if route_id is not None:
            print("route_idroute_idroute_idroute_idroute_idroute_idroute_idroute_idroute_idroute_idroute_idroute_id")
            try:
                route = Route.objects.get(is_active=True, id=route_id)
                trip.route = route
            except Route.DoesNotExist:
                return UpdateTrip(ok=False, trip=None, error="Route not found")

        if vessel_id is not None:
            print("vessel_idvessel_idvessel_idvessel_idvessel_idvessel_idvessel_idvessel_id")
            try:
                vessel = Vessel.objects.get(is_active=True, id=vessel_id)
                trip.vessel = vessel
            except Vessel.DoesNotExist:
                return UpdateTrip(ok=False, trip=None, error="Vessel not found")

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

    get_trip_list = graphene.Field(
        TripPaginationType,
        page=graphene.Int(required=False),
    )

    @login_required
    def resolve_get_trip_by_id(root, info, id) -> Trip:
        if len(id) == settings.SHORT_ID_SIZE:
            return Trip.objects.get(
                is_active=True,
                id__startswith=id,
            )
        return Trip.objects.get(is_active=True, id=id)

    @login_required
    def resolve_get_trip_list(root, info, page=1):
        queryset = Trip.objects.filter(is_active=True).order_by("-create_at")
        result = get_paginated_query(queryset, page)
        return TripPaginationType(
            results=result["results"],
            pages=result["pages"],
            count=result["count"],
            next=result["next"],
        )


schema = graphene.Schema(query=Query, mutation=Mutation)
