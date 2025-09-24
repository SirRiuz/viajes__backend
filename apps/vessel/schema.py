import graphene
from django.conf import settings
from graphql_jwt.decorators import login_required

from apps.vessel.models import Vessel
from apps.vessel.types import VesselType
from apps.vessel.types import VesselPaginationType
from apps.default.methods.pagination import get_paginated_query


class CreateVessel(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        seat_count = graphene.Int(required=True)

    ok = graphene.Boolean()
    vessel = graphene.Field(VesselType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, name, seat_count):
        try:
            vessel = Vessel.objects.create(name=name, seat_count=seat_count)
            return CreateVessel(ok=True, vessel=vessel, error=None)
        except Exception as e:
            return CreateVessel(ok=False, vessel=None, error=str(e))


class UpdateVessel(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)
        name = graphene.String(required=False)
        seat_count = graphene.Int(required=False)

    ok = graphene.Boolean()
    vessel = graphene.Field(VesselType)
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, id, name=None, seat_count=None):
        try:
            vessel = Vessel.objects.get(is_active=True, id=id)
        except Vessel.DoesNotExist:
            return UpdateVessel(ok=False, vessel=None, error="Vessel not found")

        if name is not None:
            vessel.name = name
        if seat_count is not None:
            vessel.seat_count = seat_count

        vessel.save()
        return UpdateVessel(ok=True, vessel=vessel, error=None)


class DeleteVessel(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @staticmethod
    @login_required
    def mutate(root, info, id):
        try:
            vessel = Vessel.objects.get(pk=id)
        except Vessel.DoesNotExist:
            return DeleteVessel(ok=False, error="Vessel not found")

        vessel.delete()

        return DeleteVessel(ok=True, error=None)


class Mutation(graphene.ObjectType):
    create_vessel = CreateVessel.Field()
    update_vessel = UpdateVessel.Field()
    delete_vessel = DeleteVessel.Field()


class Query(graphene.ObjectType):

    get_vessel_by_id = graphene.Field(
        VesselType,
        id=graphene.String(required=True),
    )

    get_vessel_list = graphene.Field(
        VesselPaginationType,
        page=graphene.Int(required=False),
    )

    get_active_vessels = graphene.List(VesselType)

    @login_required
    def resolve_get_active_vessels(root, info):
        return Vessel.objects.filter(is_active=True).order_by("-create_at")

    @login_required
    def resolve_get_vessel_by_id(root, info, id) -> Vessel:
        if len(id) == settings.SHORT_ID_SIZE:
            return Vessel.objects.get(
                is_active=True,
                id__startswith=id,
            )
        return Vessel.objects.get(is_active=True, id=id)

    @login_required
    def resolve_get_vessel_list(root, info, page=1):
        queryset = Vessel.objects.filter(is_active=True)
        result = get_paginated_query(queryset, page)
        return VesselPaginationType(
            results=result["results"],
            pages=result["pages"],
            count=result["count"],
            next=result["next"],
        )


schema = graphene.Schema(query=Query, mutation=Mutation)
