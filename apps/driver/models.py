# Django
from django.db import models

# Libs
from apps.default.models.base_model import BaseModel


class Driver(BaseModel):

    full_name = models.CharField(max_length=250)
    dni = models.CharField(max_length=150, unique=True)
    license_id = models.CharField(max_length=150, null=True)

    dni_pdf = models.FileField(upload_to="drivers/dni/", null=True, blank=True)
    license_pdf = models.FileField(upload_to="drivers/license/", null=True, blank=True)
    signature = models.FileField(upload_to="drivers/signature/", null=True, blank=True)

    def __str__(self):
        return self.full_name
