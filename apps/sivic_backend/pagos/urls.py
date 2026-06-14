from django.urls import path
from . import views

urlpatterns = [
    path("",                                   views.PagoListView.as_view(),          name="pagos-lista"),
    path("checkout/",                          views.CrearCheckoutView.as_view(),     name="pagos-checkout"),
    path("webhook/",                           views.webhook_stripe,                  name="pagos-webhook"),
    path("reportes/",                          views.ReporteMensualListView.as_view(), name="pagos-reportes"),
    path("suscripcion/<int:condominio_id>/",   views.SuscripcionEstadoView.as_view(), name="pagos-suscripcion"),
]
