# Django
from django.conf import settings


def get_trusted_client_ip(request) -> str:
    """
    Client IP that the client can't forge. Each of the TRUSTED_PROXY_COUNT
    reverse proxies (nginx = 1) appends the address it saw to
    X-Forwarded-For, so the real client is the Nth entry from the right;
    whatever the client wrote further left is ignored. Behind Cloudflare,
    nginx restores the visitor's address first (nginx/real_ip.conf).
    """
    forwarded = [ip.strip() for ip in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if ip.strip()]
    hops = settings.TRUSTED_PROXY_COUNT
    if hops > 0 and len(forwarded) >= hops:
        return forwarded[-hops]
    return request.META.get("REMOTE_ADDR", "")
