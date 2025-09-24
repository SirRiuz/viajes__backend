# Django
from django.conf import settings

# Libs
import graphene
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectType

# Models
from apps.route.models import Route


class RouteType(DjangoObjectType):

    short_id = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    class Meta:
        model = Route
        fields = (
            "id",
            "route_name",
            "created_at",
            "updated_at",
        )


class RoutePaginationType(graphene.ObjectType):
    results = graphene.List(RouteType)
    count = graphene.Int()
    pages = graphene.Int()
    next = graphene.Int()
