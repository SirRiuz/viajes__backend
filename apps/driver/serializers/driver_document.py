# Django
from rest_framework import serializers

# Models
from apps.driver.models import Driver


class DriverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ["id", "dni_pdf", "license_pdf"]
        extra_kwargs = {
            "dni_pdf": {"required": False},
            "license_pdf": {"required": False},
        }
