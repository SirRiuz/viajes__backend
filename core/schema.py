# Models
from apps.accounts.schema import Mutation as AccountsMutation
from apps.driver.schema import Query as TreiberQuery, Mutation as TreiberMutation
from apps.trip.schema import Mutation as TripMutation, Query as TripQuery
from apps.tickets.schema import Mutation as TicketsMutation, Query as TicketsQuery
from apps.route.schema import Mutation as RouteMutation, Query as RouteQuery
from apps.vessel.schema import Query as VesselQuery, Mutation as VesselMutation

# Libs
import graphene


class Query(
    TicketsQuery,
    TreiberQuery,
    TripQuery,
    RouteQuery,
    VesselQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    TicketsMutation,
    TreiberMutation,
    AccountsMutation,
    TripMutation,
    RouteMutation,
    VesselMutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
