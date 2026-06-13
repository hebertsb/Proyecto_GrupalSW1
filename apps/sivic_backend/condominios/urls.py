from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("planes",        views.PlanViewSet,        basename="plan")
router.register("",              views.CondominioViewSet,  basename="condominio")
router.register("suscripciones", views.SuscripcionViewSet, basename="suscripcion")

urlpatterns = [path("", include(router.urls))]
