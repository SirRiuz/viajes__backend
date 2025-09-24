# Django
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions

# Libs
from graphene_django.views import GraphQLView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


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

urlpatterns = [
    path(
        "staff/tools/swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("staff/tools/", admin.site.urls),
    path("admin/", include("apps.honeypot.urls")),
    path("", include("apps.healthcheck.urls")),
    path("graphiql/", GraphQLView.as_view(graphiql=True)),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=False))),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
