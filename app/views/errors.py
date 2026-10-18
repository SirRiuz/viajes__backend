"""
Error answers without a framework's signature. Django's own pages («The
requested resource was not found on this server.», «CSRF verification
failed») tell fingerprinting tools (Wappalyzer, WhatWeb…) what serves the
site; these are a bare status line like any server's. Only used with DEBUG
off: Django keeps its detailed pages while developing.
"""

# Django
from django.http import HttpResponse


def _plain(status: int, reason: str) -> HttpResponse:
    return HttpResponse(reason, status=status, content_type="text/plain; charset=utf-8")


def bad_request(request, exception=None):
    return _plain(400, "Bad Request")


def permission_denied(request, exception=None):
    return _plain(403, "Forbidden")


def page_not_found(request, exception=None):
    return _plain(404, "Not Found")


def server_error(request):
    return _plain(500, "Internal Server Error")


def csrf_failure(request, reason=""):
    return _plain(403, "Forbidden")
