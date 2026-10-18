# Django
from django.db import IntegrityError, models, transaction
from django.db.models import Max

# Models
from app.models.base_model import BaseModel

# Two sales at the same moment read the same MAX(index): the second insert
# hits the unique constraint. It retries with a fresh number instead of
# failing the request.
INDEX_RETRIES = 3


class IndexedModel(BaseModel):
    """BaseModel with a human-friendly sequential number (1, 2, 3…)."""

    index = models.PositiveBigIntegerField(
        unique=True,
        editable=False,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if self.index is not None:
            return super().save(*args, **kwargs)

        for attempt in range(INDEX_RETRIES):
            last_index = type(self).objects.aggregate(Max("index"))["index__max"] or 0
            self.index = last_index + 1
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.index = None
                if attempt == INDEX_RETRIES - 1:
                    raise

    class Meta:
        abstract = True
