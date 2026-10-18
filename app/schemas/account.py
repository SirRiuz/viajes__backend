# Libs
import graphene
import graphql_jwt
from graphql import GraphQLError
from graphql_jwt.exceptions import JSONWebTokenError

# Utils
from app.utils import rate_limit
from app.utils.client import get_trusted_client_ip

# Types
from app.types.accounts import UserType

# Constants
from constants.exceptions import ErrorMessages

# Failed log-ins allowed per address in the window; successful ones are free
LOGIN_MAX_FAILURES = 10
LOGIN_WINDOW_S = 15 * 60


class ObtainJSONWebToken(graphql_jwt.ObtainJSONWebToken):
    """`tokenAuth`, with a cap on failed attempts per address (brute force)."""

    class Meta:
        name = "ObtainJSONWebToken"

    @classmethod
    def mutate(cls, root, info, **kwargs):
        key = f"token-auth:{get_trusted_client_ip(info.context)}"
        if rate_limit.blocked(key, LOGIN_MAX_FAILURES):
            raise GraphQLError(ErrorMessages.TOO_MANY_LOGIN_ATTEMPTS)
        try:
            return super().mutate(root, info, **kwargs)
        except JSONWebTokenError:
            rate_limit.hit(key, LOGIN_MAX_FAILURES, LOGIN_WINDOW_S)
            raise


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            return None

        return user


class Mutation(graphene.ObjectType):
    token_auth = ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
