# Django
from django.db import models
from django.db.models import Max

# Libs
from apps.default.models.base_model import BaseModel

# Models
from apps.driver.models import Driver
from apps.route.models import Route
from apps.vessel.models import Vessel


class Trip(BaseModel):

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    vessel = models.ForeignKey(Vessel, on_delete=models.CASCADE)
    dispatcher = models.CharField(blank=True, null=True)
    index = models.PositiveBigIntegerField(
        unique=True,
        editable=False,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if self.index is None:
            last_index = Trip.objects.aggregate(Max("index"))["index__max"] or 0
            self.index = last_index + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.id
