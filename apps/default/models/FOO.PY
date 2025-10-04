# Python
import uuid
import hashlib
from datetime import datetime, timezone, timedelta

# Django
from django.db import models
# from django.utils import timezone


BOGOTA_TZ = timezone(timedelta(hours=-5))


class BaseModel(models.Model):
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField()
    update_at = models.DateTimeField()
    id = models.CharField(
        primary_key=True,
        unique=True,
        default="Empty",
        editable=False,
        max_length=255,
    )

    def save(self, *args, **kwargs):
        now = datetime.now(BOGOTA_TZ)
        if self._state.adding:
            self.id = str(hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest())
            self.create_at = now

        self.update_at = now
        super().save(*args, **kwargs)

    def disable(self):
        self.is_active = False
        self.save()

    class Meta:
        abstract = True
