from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register("zonas-roi", views.ZonaRoiViewSet, basename="zona-roi")
router.register("",          views.CamaraViewSet,  basename="camara")

urlpatterns = [
    # Endpoints personalizados (deben ir ANTES del router genérico)
    path("<int:pk>/stream/",      views.stream_camara,   name="camara-stream"),
    path("<int:pk>/analizar_ia/",    views.analizar_ia,    name="camara-analizar-ia"),
    path("<int:pk>/analizar_local/", views.analizar_local, name="camara-analizar-local"),
    path("<int:pk>/ultimo_frame/",   views.ultimo_frame,   name="camara-ultimo-frame"),
    path("analizar/",             views.analizar_frame,          name="camara-analizar"),
    path("analizar_persona/",     views.analizar_frame_persona,  name="camara-analizar-persona"),
    path("probar/",               views.probar_conexion, name="camara-probar"),
    # Planos del condominio
    path("planos/",                                          views.planos_list,     name="plano-list"),
    path("planos/<int:pk>/",                                 views.plano_detail,    name="plano-detail"),
    path("planos/<int:plano_pk>/posiciones/",                views.posiciones_list, name="posicion-list"),
    path("planos/<int:plano_pk>/posiciones/<int:camara_pk>/", views.posicion_detail, name="posicion-detail"),
    path("planos/<int:plano_pk>/posiciones/<int:camara_pk>/imagenes/",                  views.imagenes_zona_list,  name="imagen-zona-list"),
    path("planos/<int:plano_pk>/posiciones/<int:camara_pk>/imagenes/<int:imagen_pk>/",  views.imagen_zona_detail,  name="imagen-zona-detail"),
    path("", include(router.urls)),
]
