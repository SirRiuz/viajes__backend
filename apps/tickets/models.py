# Django
from django.db import models
from django.db.models import Max

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
    index = models.PositiveBigIntegerField(unique=True, editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.index is None:
            last_index = Ticket.objects.aggregate(Max("index"))["index__max"] or 0
            self.index = last_index + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.id
