from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("zonas-roi", views.ZonaRoiViewSet, basename="zona-roi")
router.register("",          views.CamaraViewSet,  basename="camara")

urlpatterns = [
    # Endpoints personalizados (deben ir ANTES del router genérico)
    path("<int:pk>/stream/", views.stream_camara,   name="camara-stream"),
    path("analizar/",        views.analizar_frame,  name="camara-analizar"),
    path("probar/",          views.probar_conexion, name="camara-probar"),
    path("", include(router.urls)),
]
