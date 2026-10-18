# Django
from django.conf import settings
from rest_framework.views import exception_handler

# Generic «detail» per status, instead of Django REST framework's own
# sentences («Authentication credentials were not provided.»), which give it
# away. Field validation errors (400 with field names) are kept: they are the
# API's answer, not the framework's.
GENERIC_DETAIL = {
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    415: "Unsupported Media Type",
    429: "Too Many Requests",
}


def exception_handler_without_signature(exc, context):
    response = exception_handler(exc, context)
    if response is None or settings.DEBUG:
        return response

    if isinstance(response.data, dict) and set(response.data) == {"detail"}:
        response.data = {"detail": GENERIC_DETAIL.get(response.status_code, "Error")}
    return response
