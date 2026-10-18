# Libs
from graphql_jwt.exceptions import JSONWebTokenError
from graphql_jwt.shortcuts import get_user_by_token
from graphql_jwt.utils import get_credentials
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JSONWebTokenAuthentication(BaseAuthentication):
    """
    DRF twin of graphql_jwt's middleware: the REST views accept the same
    `Authorization: JWT <token>` the frontend sends to GraphQL.
    """

    keyword = "JWT"

    def authenticate(self, request):
        token = get_credentials(request._request)
        if not token:
            return None

        try:
            user = get_user_by_token(token, request._request)
        except JSONWebTokenError as error:
            raise AuthenticationFailed(str(error))

        if user is None or not user.is_active:
            raise AuthenticationFailed()

        return user, token

    def authenticate_header(self, request):
        return self.keyword
