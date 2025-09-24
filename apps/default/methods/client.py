# Python
from django.conf import settings

# Libs
import geoip2.database


def get_country(address) -> str:
    """Get the country name of the user mask"""
    with geoip2.database.Reader(settings.GEOLITE_DIR) as reader:
        try:
            response = reader.city(address)
            return response.country.iso_code
        except geoip2.errors.AddressNotFoundError:
            return "Unknow"


def get_client_addres(request) -> str:
    """It is responsible for obtaining the client's IP address"""
    client = request.META.get("HTTP_X_FORWARDED_FOR")
    if client:
        client = client.split(",")[0]
    else:
        client = request.META.get("REMOTE_ADDR")

    return client
