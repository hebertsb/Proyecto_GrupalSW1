from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("", views.EventoViewSet, basename="evento")

urlpatterns = [
    path("inferencia/",            views.inferencia_ia),
    path("reportes/resumen/",      views.reportes_resumen,      name="reportes-resumen"),
    path("reportes/consulta/",     views.consulta_ia_reportes,  name="reportes-consulta"),
    # Ruta explícita: prefijo vacío en router no genera /{pk}/accion/ correctamente
    path("<int:pk>/estado/",       views.EventoViewSet.as_view({"patch": "actualizar_estado"})),
    path("", include(router.urls)),
]
