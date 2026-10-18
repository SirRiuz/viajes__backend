# Django
from django.db import models

# Models
from app.models.base_model import BaseModel


class Route(BaseModel):
    route_name = models.CharField(max_length=255)

    class Meta:
        db_table = "route_route"

    def __str__(self):
        return self.route_name
