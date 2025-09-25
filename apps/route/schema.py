import graphene

from apps.route.models import Route
from apps.route.types import RouteType
from django.conf import settings
from graphql_jwt.decorators import login_required
from apps.route.types import RoutePaginationType
from apps.default.methods.pagination import get_paginated_query


class Query(graphene.ObjectType):

    get_active_routes = graphene.List(RouteType)

    get_route_list = graphene.Field(
        RoutePaginationType,
        page=graphene.Int(required=False),
    )

    get_route_by_id = graphene.Field(
        RouteType,
        id=graphene.ID(required=True),
    )

    @login_required
    def resolve_get_route_list(self, info, page=1):
        queryset = Route.objects.filter(is_active=True).order_by("-create_at")
        result = get_paginated_query(queryset, page)
        return RoutePaginationType(
            results=result["results"],
            pages=result["pages"],
            count=result["count"],
            next=result["next"],
        )

    @login_required
    def resolve_get_active_routes(self, info):
        return Route.objects.filter(is_active=True).order_by("-create_at")

    @login_required
    def resolve_get_route_by_id(self, info, id) -> Route:
        if len(id) == settings.SHORT_ID_SIZE:
            return Route.objects.get(
                is_active=True,
                id__startswith=id,
            )
        return Route.objects.get(is_active=True, id=id)


class CreateRoute(graphene.Mutation):
    class Arguments:
        route_name = graphene.String(required=True)

    route = graphene.Field(RouteType)

    @staticmethod
    def mutate(root, info, route_name):
        route = Route.objects.create(route_name=route_name)
        return CreateRoute(route=route)


class UpdateRoute(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        route_name = graphene.String(required=False)

    route = graphene.Field(RouteType)

    @staticmethod
    def mutate(root, info, id, route_name=None):
        try:
            route = Route.objects.get(pk=id)
        except Route.DoesNotExist:
            raise Exception("Route not found")

        if route_name is not None:
            route.route_name = route_name

        route.save()
        return UpdateRoute(route=route)


class DeleteRoute(graphene.Mutation):
    class Arguments:
        id = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    def mutate(root, info, id):
        try:
            route = Route.objects.get(pk=id)
        except Route.DoesNotExist:
            return DeleteRoute(success=False, message="Route not found")

        route.is_active = False
        route.save()

        return DeleteRoute(success=True, message="Route deleted successfully")


class Mutation(graphene.ObjectType):
    create_route = CreateRoute.Field()
    update_route = UpdateRoute.Field()
    delete_route = DeleteRoute.Field()
