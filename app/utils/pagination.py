# Django
from django.conf import settings
from django.db.models import QuerySet
from django.core.paginator import Paginator, EmptyPage


def get_paginated_query(queryset: QuerySet, page: int) -> dict:
    """One page of ``queryset`` plus the counters the pagination types expose."""
    paginator = Paginator(queryset, settings.PAGINATION_PAGE_SIZE)
    try:
        page_data = paginator.page(page)
        next = page + 1 if page_data.has_next() else None
        results = list(page_data)
    except EmptyPage:
        results = []
        next = None

    return {
        "next": next,
        "results": results,
        "count": paginator.count,
        "pages": paginator.num_pages,
    }
