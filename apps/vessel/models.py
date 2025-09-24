# Django
from django.db import models

# Libs
from apps.default.models.base_model import BaseModel


class Vessel(BaseModel):

    name = models.CharField(max_length=255)
    seat_count = models.PositiveIntegerField()

    def __str__(self):
        return self.id
