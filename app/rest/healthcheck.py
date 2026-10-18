# Django
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class HealthcheckView(APIView):
    # Hit by monitors all day: no session or user lookup
    authentication_classes = ()

    def get(self, request) -> Response:
        """
        It is responsible for validating that the service is
        functioning, so the response will always be 'ok';
        otherwise, it will return an error.
        ---
        Content/Type:
            application/json
        ---
        Response body:

            "ok"
        ---
        Response codes:

            200 - It will return an 'ok' if everything is working.
        """
        return Response("ok", status=status.HTTP_200_OK)
