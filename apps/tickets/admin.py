# Django
from django.contrib import admin
from django.conf import settings

# Models
from apps.tickets.models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "client_name",
        "client_email",
        "ticket_price",
        "seat_number",
        "create_at",
        "is_active",
    )

    def short_id(self, obj) -> str:
        return obj.id[: settings.SHORT_ID_SIZE]

    short_id.short_description = "ID"
