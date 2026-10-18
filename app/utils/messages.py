# Django
from django.contrib.messages.storage.cookie import CookieStorage


class FlashCookieStorage(CookieStorage):
    """Django's message cookie under a name that doesn't give it away («messages»)."""

    cookie_name = "flash"
