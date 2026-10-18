# Libs
import graphene


def pagination_type(name: str, item_type) -> type:
    """
    `{name}` GraphQL object with one page of `item_type` and its counters
    (the dict returned by app.utils.pagination.get_paginated_query).
    """
    return type(
        name,
        (graphene.ObjectType,),
        {
            "results": graphene.List(item_type),
            "count": graphene.Int(),
            "pages": graphene.Int(),
            "next": graphene.Int(),
        },
    )
