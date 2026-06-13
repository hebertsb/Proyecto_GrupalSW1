from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("historial", views.NotificacionViewSet, basename="notificacion")

urlpatterns = [
    path("push/",  views.enviar_push),
    path("email/", views.enviar_email),
    path("", include(router.urls)),
]
