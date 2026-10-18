# Libs
import graphene

# Queries and Mutations
from app.schemas.account import Query as AccountQuery, Mutation as AccountMutation
from app.schemas.driver import Query as DriverQuery, Mutation as DriverMutation
from app.schemas.route import Query as RouteQuery, Mutation as RouteMutation
from app.schemas.ticket import Query as TicketQuery, Mutation as TicketMutation
from app.schemas.trip import Query as TripQuery, Mutation as TripMutation
from app.schemas.vessel import Query as VesselQuery, Mutation as VesselMutation


class Query(
    TicketQuery,
    DriverQuery,
    TripQuery,
    RouteQuery,
    VesselQuery,
    AccountQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    TicketMutation,
    DriverMutation,
    AccountMutation,
    TripMutation,
    RouteMutation,
    VesselMutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
