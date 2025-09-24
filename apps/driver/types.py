# Django
from django.conf import settings

# Models
from apps.driver.models import Driver

# Libs
import graphene
from graphene_django.types import DjangoObjectType


class DriverType(DjangoObjectType):

    short_id = graphene.String()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    class Meta:
        model = Driver
        fields = "__all__"


class DriverPaginationType(graphene.ObjectType):

    results = graphene.List(DriverType)
    count = graphene.Int()
    pages = graphene.Int()
    next = graphene.Int()
