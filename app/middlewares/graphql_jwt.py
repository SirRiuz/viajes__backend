# Libs
from graphql_jwt.middleware import JSONWebTokenMiddleware


class RootJSONWebTokenMiddleware(JSONWebTokenMiddleware):
    """
    graphql_jwt's middleware, run on the root fields only. The original wraps
    every field of the answer (thousands for a trip list) although the
    session is settled on the first root field: afterwards the user is set,
    or the root field already failed, and nested fields only paid the check.
    """

    def resolve(self, next, root, info, **kwargs):
        if info.path.prev is not None:
            return next(root, info, **kwargs)
        return super().resolve(next, root, info, **kwargs)
