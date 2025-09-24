# Django
from django.contrib import admin
from django.conf import settings

# Models
from apps.vessel.models import Vessel


@admin.register(Vessel)
class VesselAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "name",
        "seat_count",
        "create_at",
        "is_active",
    )

    def short_id(self, obj) -> str:
        return obj.id[: settings.SHORT_ID_SIZE]

    short_id.short_description = "ID"
