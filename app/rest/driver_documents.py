# Django
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Serializers
from app.rest.serializers.driver_document import DriverDocumentSerializer

# Models
from app.models.driver import Driver

# Auth
from app.permissions.authentication import JSONWebTokenAuthentication

# Constants
from constants.exceptions import ValidationExceptions


@api_view(["POST"])
@authentication_classes([JSONWebTokenAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_driver_documents(request, driver_id):
    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return Response(
            {"error": ValidationExceptions.DRIVER_NOT_FOUND},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = DriverDocumentSerializer(driver, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
