# Django
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


# Models
from app.models.base_model import BaseModel
from honeypot.models.login_attempt import LoginAttempt


# Libs
from honeypot.app_settings import HONEYPOT_LOGIN_TRYOUT

BLACKLIST_CACHE_KEY = "honeypot:blacklist"
BLACKLIST_CACHE_S = 300


def is_blacklisted(ip: str) -> bool:
    """Checked on every request: the whole list lives in the cache."""
    if not ip:
        return False
    ips = cache.get(BLACKLIST_CACHE_KEY)
    if ips is None:
        ips = frozenset(BlackList.objects.exclude(ip_address=None).values_list("ip_address", flat=True))
        cache.set(BLACKLIST_CACHE_KEY, ips, BLACKLIST_CACHE_S)
    return ip in ips


class BlackList(BaseModel):
    created_date = models.DateTimeField(_("created_date"), auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        _("ip address"), protocol="both", blank=True, null=True
    )

    class Meta:
        ordering = ("-created_date",)

    def __str__(self):
        return self.ip_address


@receiver(post_save, sender=BlackList)
@receiver(post_delete, sender=BlackList)
def refresh_blacklist_cache(sender, **kwargs):
    cache.delete(BLACKLIST_CACHE_KEY)


@receiver(post_delete, sender=BlackList)
def remove_all_related_attempts(sender, instance, **kwargs):
    LoginAttempt.objects.filter(ip_address=instance.ip_address).delete()


@receiver(post_save, sender=LoginAttempt)
def create_blacklist(sender, instance, created, **kwargs):
    if (
        created
        and LoginAttempt.objects.filter(ip_address=instance.ip_address).count()
        >= HONEYPOT_LOGIN_TRYOUT
    ):
        BlackList.objects.get_or_create(ip_address=instance.ip_address)
