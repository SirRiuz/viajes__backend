# Django
from django.conf import settings
from django.db.models import QuerySet


def get_active_by_id(queryset: QuerySet, id: str):
    """
    Active row by its full id or by its short id (the first SHORT_ID_SIZE
    characters shown in the UI). Raises the model's DoesNotExist.
    """
    if len(id) == settings.SHORT_ID_SIZE:
        return queryset.get(is_active=True, id__startswith=id)

    return queryset.get(is_active=True, id=id)
