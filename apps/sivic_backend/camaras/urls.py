from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("zonas-roi", views.ZonaRoiViewSet, basename="zona-roi")
router.register("",          views.CamaraViewSet,  basename="camara")

urlpatterns = [path("", include(router.urls))]
