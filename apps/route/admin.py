# Django
from django.contrib import admin
from django.conf import settings

# Models
from apps.route.models import Route


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "route_name",
        "create_at",
        "is_active",
    )

    def short_id(self, obj) -> str:
        return obj.id[: settings.SHORT_ID_SIZE]

    short_id.short_description = "ID"
