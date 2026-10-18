# Python
import logging
from functools import lru_cache

# Django
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db import connection, transaction
from django.http import HttpResponseNotAllowed

# Libs
from graphene_django.constants import MUTATION_ERRORS_FLAG
from graphene_django.settings import graphene_settings
from graphene_django.views import GraphQLView, HttpError
from graphql import ExecutionResult, GraphQLError, OperationType, execute, get_operation_ast, parse, validate
from graphql_jwt.exceptions import JSONWebTokenError

from app.utils.graphql_limits import MAX_QUERY_CHARS, MAX_TOKENS, validation_rules

LOGGER = logging.getLogger(__name__)
GENERIC_ERROR = "Something went wrong."
# Syntax, validation, limits, introspection and variable errors: the GraphQL
# server's own wording names it (graphw00f fingerprints engines that way) and
# its «Did you mean…?» hints give the schema away field by field.
INVALID_QUERY = "Invalid query."

# Errors whose message is meant for the client: our own («Route not found»),
# «… matching query does not exist» and the JWT ones («You do not have
# permission…», «Please enter valid credentials»), which the frontend reads.
PUBLIC_ERRORS = (GraphQLError, ValidationError, ObjectDoesNotExist, MultipleObjectsReturned, JSONWebTokenError)

# Parsed and validated documents kept per process. The frontend sends the
# same few dozen documents over and over; anything else just rotates out.
DOCUMENT_CACHE_SIZE = 256


@lru_cache(maxsize=DOCUMENT_CACHE_SIZE)
def prepare_document(schema, rules, query):
    """
    (document, syntax error, validation errors) of one query string. Django
    builds a view instance per request, so the cache lives here. The AST and
    the errors are never modified afterwards: safe to share between threads.
    """
    try:
        document = parse(query, max_tokens=MAX_TOKENS)
    except GraphQLError as error:
        return None, error, None
    errors = validate(schema, document, rules, graphene_settings.MAX_VALIDATION_ERRORS)
    return document, None, errors


class ProtectedGraphQLView(GraphQLView):
    """
    The GraphQL endpoint with size, depth, breadth and alias limits, no
    introspection in production (app/utils/graphql_limits.py), and internal
    errors (SQL, bugs) that never reach the client, only the logs.

    Each distinct document is parsed and validated once per process instead
    of on every request (graphene-django's flow, otherwise unchanged).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("validation_rules", tuple(validation_rules()))
        super().__init__(*args, **kwargs)

    def execute_graphql_request(self, request, data, query, variables, operation_name, show_graphiql=False):
        if not query:
            return super().execute_graphql_request(request, data, query, variables, operation_name, show_graphiql)

        # Before any parse: an oversized document is refused cheaply
        if len(query) > MAX_QUERY_CHARS:
            return ExecutionResult(errors=[GraphQLError("Query too large.")])

        document, syntax_error, validation_errors = prepare_document(
            self.schema.graphql_schema, tuple(self.validation_rules), query
        )
        if syntax_error is not None:
            return ExecutionResult(errors=[syntax_error])

        operation_ast = get_operation_ast(document, operation_name)
        if request.method.lower() == "get" and operation_ast is not None and operation_ast.operation != OperationType.QUERY:
            if show_graphiql:
                return None
            raise HttpError(
                HttpResponseNotAllowed(
                    ["POST"],
                    f"Can only perform a {operation_ast.operation.value} operation from a POST request.",
                )
            )

        if validation_errors:
            return ExecutionResult(data=None, errors=validation_errors)

        schema = self.schema.graphql_schema
        try:
            execute_options = {
                "root_value": self.get_root_value(request),
                "context_value": self.get_context(request),
                "variable_values": variables,
                "operation_name": operation_name,
                "middleware": self.get_middleware(request),
            }
            if self.execution_context_class:
                execute_options["execution_context_class"] = self.execution_context_class

            if (
                operation_ast is not None
                and operation_ast.operation == OperationType.MUTATION
                and (
                    graphene_settings.ATOMIC_MUTATIONS is True
                    or connection.settings_dict.get("ATOMIC_MUTATIONS", False) is True
                )
            ):
                with transaction.atomic():
                    result = execute(schema, document, **execute_options)
                    if getattr(request, MUTATION_ERRORS_FLAG, False) is True:
                        transaction.set_rollback(True)
                return result

            return execute(schema, document, **execute_options)
        except Exception as e:
            return ExecutionResult(errors=[e])

    @staticmethod
    def format_error(error):
        """
        In production only the resolvers' public errors keep their message
        (the frontend reads them); everything else is one of two generic
        sentences, and an internal error's detail goes to the logs. With DEBUG
        on every message is the real one.
        """
        if settings.DEBUG:
            return GraphQLView.format_error(error)

        # Raised outside execution (caught in execute_graphql_request)
        if isinstance(error, HttpError):
            return {"message": INVALID_QUERY}
        if not isinstance(error, GraphQLError):
            LOGGER.error("GraphQL request error", exc_info=error)
            return {"message": GENERIC_ERROR}
        # Only a field's resolver error has a path; syntax, validation and
        # variable errors (whatever they wrap) belong to the query itself
        if error.path is None:
            return {"message": INVALID_QUERY}
        original = error.original_error
        if original is not None and not isinstance(original, PUBLIC_ERRORS):
            LOGGER.error("GraphQL resolver error", exc_info=original)
            return {"message": GENERIC_ERROR}
        return GraphQLView.format_error(error)
