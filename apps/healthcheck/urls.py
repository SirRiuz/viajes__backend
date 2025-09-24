# Django
from django.urls import path

# Views
from apps.healthcheck.views.healthcheck_view import HealthcheckView


urlpatterns = [
    path("healthcheck/", HealthcheckView.as_view()),
]
