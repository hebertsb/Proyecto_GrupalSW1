from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("", views.EventoViewSet, basename="evento")

urlpatterns = [
    path("inferencia/", views.inferencia_ia),
    path("", include(router.urls)),
]
