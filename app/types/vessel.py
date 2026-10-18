# Django
from django.conf import settings

# Libs
import graphene
from graphene_django.types import DjangoObjectType

# Models
from app.models.vessel import Vessel

# Types
from app.types.pagination import pagination_type


class VesselType(DjangoObjectType):

    short_id = graphene.String()
    name = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    def resolve_name(self, info):
        return self.name.capitalize()

    class Meta:
        model = Vessel
        fields = (
            "id",
            "name",
            "seat_count",
        )


VesselPaginationType = pagination_type("VesselPaginationType", VesselType)
