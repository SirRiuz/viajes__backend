# Django
from django.db import models
from django.db.models import Prefetch

# Models
from app.models.driver import Driver
from app.models.indexed_model import IndexedModel
from app.models.route import Route
from app.models.vessel import Vessel


class TripQuerySet(models.QuerySet):
    def with_details(self, prefix=""):
        """
        Everything TripType reads, in 2 queries for any number of trips:
        driver, route and vessel joined, active tickets prefetched into
        `active_tickets` (newest first). `prefix` reaches the trips through a
        relation, e.g. "trip__" from a Ticket queryset.
        """
        from app.models.ticket import Ticket

        return self.select_related(
            f"{prefix}driver",
            f"{prefix}route",
            f"{prefix}vessel",
        ).prefetch_related(
            Prefetch(
                f"{prefix}ticket_set",
                queryset=Ticket.objects.filter(is_active=True).order_by("-create_at"),
                to_attr="active_tickets",
            )
        )


class Trip(IndexedModel):

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    vessel = models.ForeignKey(Vessel, on_delete=models.CASCADE)
    dispatcher = models.CharField(blank=True, null=True)

    objects = TripQuerySet.as_manager()

    class Meta:
        db_table = "trip_trip"

    def __str__(self):
        return self.id

    def get_active_tickets(self) -> list:
        """Active tickets, newest first; one query per trip at most."""
        if not hasattr(self, "active_tickets"):
            self.active_tickets = list(self.ticket_set.filter(is_active=True).order_by("-create_at"))
        return self.active_tickets
