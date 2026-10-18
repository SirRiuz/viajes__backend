from django.http import HttpResponseForbidden

from constants.exceptions import ErrorMessages


def superuser_required(view_func):
    """Decorator that restricts access to superusers only."""

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return HttpResponseForbidden(
                ErrorMessages.ACCESS_DENIED_SUPERUSER_REQUIRED,
            )

        return view_func(request, *args, **kwargs)

    return wrapper
