from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("eventos-dataset", views.DatasetEventoViewSet, basename="dataset-evento")
router.register("",               views.DatasetViewSet,        basename="dataset")

urlpatterns = [path("", include(router.urls))]
