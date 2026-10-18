# Libs
import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

# Models
from app.models.route import Route

# Types
from app.types.route import RouteType, RoutePaginationType

# Utils
from app.utils.lookup import get_active_by_id
from app.utils.pagination import get_paginated_query

# Constants
from constants.exceptions import ValidationExceptions


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
        return RoutePaginationType(**get_paginated_query(queryset, page))

    @login_required
    def resolve_get_active_routes(self, info):
        return Route.objects.filter(is_active=True).order_by("-create_at")

    @login_required
    def resolve_get_route_by_id(self, info, id) -> Route:
        return get_active_by_id(Route.objects.all(), id)


class CreateRoute(graphene.Mutation):
    class Arguments:
        route_name = graphene.String(required=True)

    route = graphene.Field(RouteType)

    @staticmethod
    @login_required
    def mutate(root, info, route_name):
        route = Route.objects.create(route_name=route_name)
        return CreateRoute(route=route)


class UpdateRoute(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        route_name = graphene.String(required=False)

    route = graphene.Field(RouteType)

    @staticmethod
    @login_required
    def mutate(root, info, id, route_name=None):
        try:
            route = Route.objects.get(pk=id)
        except Route.DoesNotExist:
            raise GraphQLError(ValidationExceptions.ROUTE_NOT_FOUND)

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
    @login_required
    def mutate(root, info, id):
        try:
            route = Route.objects.get(pk=id)
        except Route.DoesNotExist:
            return DeleteRoute(success=False, message=ValidationExceptions.ROUTE_NOT_FOUND)

        route.disable()
        return DeleteRoute(success=True, message=ValidationExceptions.ROUTE_DELETED)


class Mutation(graphene.ObjectType):
    create_route = CreateRoute.Field()
    update_route = UpdateRoute.Field()
    delete_route = DeleteRoute.Field()
