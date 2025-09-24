# Libs
import graphene
from django.conf import settings
from graphene_django import DjangoObjectType

# Models
from apps.vessel.models import Vessel


class VesselType(DjangoObjectType):

    short_id = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    class Meta:
        model = Vessel
        fields = (
            "id",
            "name",
            "seat_count",
            "created_at",
            "updated_at",
        )


class VesselPaginationType(graphene.ObjectType):
    results = graphene.List(VesselType)
    count = graphene.Int()
    pages = graphene.Int()
    next = graphene.Int()
