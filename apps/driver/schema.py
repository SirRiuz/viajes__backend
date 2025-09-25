# Libs
import graphene
from graphql_jwt.decorators import login_required
from apps.default.methods.pagination import get_paginated_query
from apps.driver.types import DriverType, DriverPaginationType

# Django
from django.conf import settings

# Models
from apps.driver.models import Driver


class Query(graphene.ObjectType):

    get_driver_list = graphene.Field(
        DriverPaginationType,
        page=graphene.Int(required=False),
    )

    get_driver_by_id = graphene.Field(
        DriverType,
        id=graphene.ID(required=True),
    )

    get_active_drivers = graphene.List(DriverType)

    @login_required
    def resolve_get_driver_list(self, info, page=1):
        queryset = Driver.objects.filter(is_active=True).order_by("-create_at")
        result = get_paginated_query(queryset, page)
        return DriverPaginationType(
            results=result["results"],
            pages=result["pages"],
            count=result["count"],
            next=result["next"],
        )

    @login_required
    def resolve_get_active_drivers(self, info):
        return Driver.objects.filter(is_active=True).order_by("-create_at")

    @login_required
    def resolve_get_driver_by_id(self, info, id) -> Driver:
        if len(id) == settings.SHORT_ID_SIZE:
            return Driver.objects.get(
                is_active=True,
                id__startswith=id,
            )

        return Driver.objects.get(is_active=True, id=id)


class CreateDriver(graphene.Mutation):
    class Arguments:
        full_name = graphene.String(required=True)
        dni = graphene.String(required=True)
        license_id = graphene.String(required=False)

    driver = graphene.Field(DriverType)

    @staticmethod
    def mutate(root, info, full_name, dni, license_id=None):
        driver = Driver.objects.create(
            full_name=full_name,
            dni=dni,
            license_id=license_id,
        )
        return CreateDriver(driver=driver)


class UpdateDriver(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        full_name = graphene.String(required=False)
        dni = graphene.String(required=False)
        license_id = graphene.String(required=False)

    driver = graphene.Field(DriverType)

    @staticmethod
    def mutate(root, info, id, full_name=None, dni=None, license_id=None):
        try:
            driver = Driver.objects.get(is_active=True, pk=id)
        except Driver.DoesNotExist:
            raise Exception("Driver not found")

        if full_name is not None:
            driver.full_name = full_name
        if dni is not None:
            driver.dni = dni
        if license_id is not None:
            driver.license_id = license_id

        driver.save()
        return UpdateDriver(driver=driver)


class DeleteDriver(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @staticmethod
    def mutate(root, info, id):
        try:
            driver = Driver.objects.get(pk=id)
        except Driver.DoesNotExist:
            return DeleteDriver(ok=False, error="Driver not found")

        driver.is_active = False
        driver.save()
        return DeleteDriver(ok=True, error=None)


class Mutation(graphene.ObjectType):
    create_driver = CreateDriver.Field()
    update_driver = UpdateDriver.Field()
    delete_driver = DeleteDriver.Field()
