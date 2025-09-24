# Django
from django.db import models

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

    def __str__(self):
        return self.id
