from django.conf import settings
from django.http import HttpResponse

from app.utils import rate_limit
from app.utils.client import get_trusted_client_ip
from constants.exceptions import ErrorMessages

# Django's admin has no limit on log-in attempts of its own
MAX_ATTEMPTS = 10
WINDOW_S = 15 * 60


class AdminLoginThrottleMiddleware:
    """At most 10 admin log-in attempts per address every 15 minutes."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_path = f"/{settings.INTERNAL_ADMIN_URL.strip('/')}/login/"

    def __call__(self, request):
        if request.method == "POST" and request.path == self.login_path:
            if not rate_limit.hit(f"admin-login:{get_trusted_client_ip(request)}", MAX_ATTEMPTS, WINDOW_S):
                return HttpResponse(ErrorMessages.TOO_MANY_LOGIN_ATTEMPTS, status=429, content_type="text/plain")
        return self.get_response(request)
