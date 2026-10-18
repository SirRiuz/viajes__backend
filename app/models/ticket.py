# Django
from django.db import models

# Models
from app.models.indexed_model import IndexedModel
from app.models.trip import Trip

# Constants
from constants.models import PAYMENT_METHOD_CHOICES


class Ticket(IndexedModel):

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

    class Meta:
        db_table = "tickets_ticket"

    def __str__(self):
        return self.id
