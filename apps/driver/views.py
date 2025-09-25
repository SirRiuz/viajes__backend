# Django
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

# Serializers
from apps.driver.serializers.driver_document import DriverDocumentSerializer

# Model
from apps.driver.models import Driver


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_driver_documents(request, driver_id):
    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return Response(
            {"error": "Driver not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = DriverDocumentSerializer(driver, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
