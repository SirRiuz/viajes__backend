# Django
from django.conf import settings

# Models
from apps.driver.models import Driver

# Libs
import graphene
from graphene_django.types import DjangoObjectType


class DriverType(DjangoObjectType):

    short_id = graphene.String()
    dni_file_url = graphene.String()
    license_pdf_file_url = graphene.String()
    signature_url = graphene.String()
    full_name = graphene.String()

    def resolve_full_name(self, info):
        return self.full_name.capitalize()

    def resolve_short_id(self, info):
        return self.id[: settings.SHORT_ID_SIZE]

    def resolve_dni_file_url(self, info):
        if self.dni_pdf:
            request = info.context.build_absolute_uri
            return request(self.dni_pdf.url)

        return None

    def resolve_signature_url(self, info):
        if self.signature:
            request = info.context.build_absolute_uri
            return request(self.signature.url)

        return None

    def resolve_license_pdf_file_url(self, info):
        if self.license_pdf:
            request = info.context.build_absolute_uri
            return request(self.license_pdf.url)

        return None

    class Meta:
        model = Driver
        fields = "__all__"


class DriverPaginationType(graphene.ObjectType):

    results = graphene.List(DriverType)
    count = graphene.Int()
    pages = graphene.Int()
    next = graphene.Int()
