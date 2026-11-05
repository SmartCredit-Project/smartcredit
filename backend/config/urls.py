from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentification et gestion des utilisateurs
    path("api/auth/", include("accounts.urls")),
    path("api/users/", include("accounts.user_urls")),
    # Plateforme : institutions, journaux, drapeaux
    path("api/", include("accounts.platform_urls")),
    # Modules fonctionnels
    path("api/", include("applicants.urls")),
    path("api/", include("credit_applications.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/", include("predictions.urls")),
    # Documentation OpenAPI / Swagger
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
