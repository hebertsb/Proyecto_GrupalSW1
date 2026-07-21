from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("", views.PlacaRegistradaViewSet, basename="placa")
router.register("lecturas", views.LecturaPlacaViewSet, basename="lectura-placa")

urlpatterns = [path("", include(router.urls))]
