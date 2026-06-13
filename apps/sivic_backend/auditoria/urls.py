from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("logs", views.LogAuditoriaViewSet, basename="log-auditoria")

urlpatterns = [path("", include(router.urls))]
