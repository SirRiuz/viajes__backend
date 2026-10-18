# Django
from django.db import models

# Models
from app.models.base_model import BaseModel


class Vessel(BaseModel):

    name = models.CharField(max_length=255)
    seat_count = models.PositiveIntegerField()

    class Meta:
        db_table = "vessel_vessel"

    def __str__(self):
        return self.id
