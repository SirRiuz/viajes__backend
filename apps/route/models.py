# Django
from django.db import models

# Libs
from apps.default.models.base_model import BaseModel


class Route(BaseModel):
    route_name = models.CharField(max_length=255)

    def __str__(self):
        return self.route_name
