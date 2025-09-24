# Django
from django.db import models

# Libs
from apps.default.models.base_model import BaseModel

# Models
from apps.trip.models import Trip


PAYMENT_METHOD_CHOICES = [
    ("cash", "Cash"),
    ("transfer", "Transfer"),
]


class Ticket(BaseModel):

    client_name = models.CharField(max_length=255)
    client_id_number = models.CharField(max_length=50)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=20)

    ticket_price = models.CharField(max_length=255)
    seat_number = models.PositiveIntegerField()
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cash",
    )

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)

    def __str__(self):
        return self.id
