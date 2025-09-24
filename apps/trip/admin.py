# Django
from django.contrib import admin
from django.conf import settings

# Models
from apps.trip.models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "create_at",
        "is_active",
    )

    def short_id(self, obj) -> str:
        return obj.id[: settings.SHORT_ID_SIZE]

    short_id.short_description = "ID"
