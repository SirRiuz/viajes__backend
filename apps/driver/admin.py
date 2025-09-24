# Django
from django.contrib import admin
from django.conf import settings

# Models
from apps.driver.models import Driver


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):

    list_display = (
        "short_id",
        "full_name",
        "create_at",
        "is_active",
    )

    def short_id(self, obj) -> str:
        return obj.id[: settings.SHORT_ID_SIZE]

    short_id.short_description = "ID"
