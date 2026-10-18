# Django
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# Models
from app.models.driver import Driver
from app.models.route import Route
from app.models.ticket import Ticket
from app.models.trip import Trip
from app.models.users import User
from app.models.vessel import Vessel


# «Django administration» / «Django site admin» name the framework on the
# log-in page; the admin keeps its look under a neutral name.
admin.site.site_header = "Administración"
admin.site.site_title = "Administración"
admin.site.index_title = "Inicio"


class ShortIdAdmin(admin.ModelAdmin):
    """List pages show the short id the UI uses instead of the full hash."""

    @admin.display(description="ID")
    def short_id(self, obj) -> str:
        return obj.id[: settings.SHORT_ID_SIZE]


@admin.register(User)
class UserAdmin(UserAdmin):
    pass


@admin.register(Driver)
class DriverAdmin(ShortIdAdmin):
    list_display = (
        "short_id",
        "full_name",
        "create_at",
        "is_active",
    )


@admin.register(Route)
class RouteAdmin(ShortIdAdmin):
    list_display = (
        "short_id",
        "route_name",
        "create_at",
        "is_active",
    )


@admin.register(Vessel)
class VesselAdmin(ShortIdAdmin):
    list_display = (
        "short_id",
        "name",
        "seat_count",
        "create_at",
        "is_active",
    )


@admin.register(Trip)
class TripAdmin(ShortIdAdmin):
    list_display = (
        "short_id",
        "create_at",
        "is_active",
    )


@admin.register(Ticket)
class TicketAdmin(ShortIdAdmin):
    list_display = (
        "short_id",
        "client_name",
        "client_email",
        "ticket_price",
        "seat_number",
        "create_at",
        "is_active",
    )
