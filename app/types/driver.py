# Django
from django.conf import settings

# Libs
import graphene
from graphene_django.types import DjangoObjectType

# Models
from app.models.driver import Driver

# Types
from app.types.pagination import pagination_type


def absolute_file_url(info, file):
    """Absolute URL of a stored file, or None when there is none."""
    if file:
        return info.context.build_absolute_uri(file.url)

    return None


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
        return absolute_file_url(info, self.dni_pdf)

    def resolve_signature_url(self, info):
        return absolute_file_url(info, self.signature)

    def resolve_license_pdf_file_url(self, info):
        return absolute_file_url(info, self.license_pdf)

    class Meta:
        model = Driver
        fields = "__all__"


DriverPaginationType = pagination_type("DriverPaginationType", DriverType)
