# Django
from django.conf import settings

# Libs
import graphene
from graphene_django.types import DjangoObjectType

# Models
from app.models.route import Route

# Types
from app.types.pagination import pagination_type


class RouteType(DjangoObjectType):

    short_id = graphene.String()
    route_name = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    def resolve_route_name(self, info):
        return self.route_name.capitalize()

    class Meta:
        model = Route
        fields = (
            "id",
            "route_name",
        )


RoutePaginationType = pagination_type("RoutePaginationType", RouteType)
