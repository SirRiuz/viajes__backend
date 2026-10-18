# Django
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden

# Libs
from app.utils.client import get_trusted_client_ip
from honeypot.models.black_list import is_blacklisted


class HoneyPotMiddleware(MiddlewareMixin):
    def process_request(self, request):
        assert hasattr(request, "session"), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE_CLASSES setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        )

        # The address nginx saw (not a forgeable X-Forwarded-For entry), and
        # the blacklist from the cache: no database query per request
        self.client_ip = get_trusted_client_ip(request)
        if is_blacklisted(self.client_ip) and not request.user.is_staff:
            return HttpResponseForbidden(
                "You are not allowed to call the website anymore."
            )
