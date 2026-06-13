from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Documentación interactiva
    path("api/schema/",  SpectacularAPIView.as_view(),     name="schema"),
    path("api/docs/",    SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",   SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),

    # Módulos SIVIC
    path("api/auth/",           include("autenticacion.urls")),
    path("api/condominios/",    include("condominios.urls")),
    path("api/camaras/",        include("camaras.urls")),
    path("api/reglas/",         include("reglas.urls")),
    path("api/eventos/",        include("eventos.urls")),
    path("api/notificaciones/", include("notificaciones.urls")),
    path("api/auditoria/",      include("auditoria.urls")),
    path("api/datasets/",       include("datasets.urls")),
]
