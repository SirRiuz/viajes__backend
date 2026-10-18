# Django
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Views
from app.rest.driver_documents import upload_driver_documents
from app.rest.healthcheck import HealthcheckView
from app.views.graphql import ProtectedGraphQLView


urlpatterns = [
    path(settings.INTERNAL_ADMIN_URL, admin.site.urls),
    path("admin/", include("honeypot.urls")),
    path("healthcheck/", HealthcheckView.as_view()),
    path(settings.INTERNAL_GRAPHQL_URL, csrf_exempt(ProtectedGraphQLView.as_view(graphiql=False)), name="graphql"),
    path("drivers/<str:driver_id>/upload-documents/", upload_driver_documents, name="upload-driver-documents"),
]

# Plain error answers, with no framework signature (only with DEBUG off)
handler400 = "app.views.errors.bad_request"
handler403 = "app.views.errors.permission_denied"
handler404 = "app.views.errors.page_not_found"
handler500 = "app.views.errors.server_error"

# Debugging tools exist only with DEBUG on: in production these paths are not
# routed at all (a plain 404, like any unknown URL) and drf_yasg isn't loaded.
if settings.DEBUG:
    from drf_yasg import openapi
    from drf_yasg.views import get_schema_view
    from graphene_django.views import GraphQLView
    from rest_framework import permissions

    from app.utils.decorators import superuser_required

    schema_view = get_schema_view(
        openapi.Info(
            title="Thriup Rest API",
            default_version="v1",
            description="Descripción de tu API",
            terms_of_service="https://www.tuapi.com/terms/",
            contact=openapi.Contact(email="contacto@tuapi.com"),
            license=openapi.License(name="Licencia de tu API"),
        ),
        public=True,
        permission_classes=(permissions.IsAdminUser,),
    )

    # Before the admin: its catch-all would answer the swagger path first
    urlpatterns = [
        path(
            f"{settings.INTERNAL_ADMIN_URL}swagger/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
        path("graphiql/", superuser_required(GraphQLView.as_view(graphiql=True))),
    ] + urlpatterns

    # Uploaded files from local disk (USE_AWS_STORAGE_SYSTEM off)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
