# Django
from django.db import models
from django.conf import settings

# Libs
from apps.default.models.base_model import BaseModel


class Driver(BaseModel):
    full_name = models.CharField(max_length=250)
    dni = models.CharField(max_length=150, unique=True)
    license_id = models.CharField(max_length=150, null=True)

    def __str__(self):
        return self.id[:settings.SHORT_ID_SIZE]
