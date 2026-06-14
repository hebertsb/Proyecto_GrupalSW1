from django.db import models
from condominios.models import Condominio, Suscripcion


class Pago(models.Model):
    pago_id                = models.AutoField(primary_key=True)
    suscripcion            = models.ForeignKey(
        Suscripcion, on_delete=models.CASCADE,
        db_column="suscripcion_id", related_name="pagos"
    )
    condominio             = models.ForeignKey(
        Condominio, on_delete=models.CASCADE,
        db_column="condominio_id", related_name="pagos"
    )
    stripe_factura_id      = models.CharField(max_length=255, unique=True)
    stripe_intento_pago_id = models.CharField(max_length=255, null=True, blank=True)
    monto                  = models.DecimalField(max_digits=10, decimal_places=2)
    moneda                 = models.CharField(max_length=3, default="usd")
    estado                 = models.CharField(max_length=20, default="open")
    periodo_inicio         = models.DateField(null=True, blank=True)
    periodo_fin            = models.DateField(null=True, blank=True)
    creado_en              = models.DateTimeField(auto_now_add=True)
    pagado_en              = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pagos"
        managed  = False


class EventoWebhookStripe(models.Model):
    stripe_evento_id = models.CharField(max_length=255, primary_key=True)
    tipo_evento      = models.CharField(max_length=100)
    procesado_en     = models.DateTimeField(auto_now_add=True)
    datos_evento     = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "eventos_webhook_stripe"
        managed  = False


class ReporteMensual(models.Model):
    reporte_id       = models.AutoField(primary_key=True)
    condominio       = models.ForeignKey(
        Condominio, on_delete=models.CASCADE,
        db_column="condominio_id", related_name="reportes"
    )
    periodo          = models.DateField()
    total_eventos    = models.IntegerField(default=0)
    eventos_parqueo  = models.IntegerField(default=0)
    eventos_mascotas = models.IntegerField(default=0)
    eventos_acceso   = models.IntegerField(default=0)
    generado_en      = models.DateTimeField(auto_now_add=True)
    enviado_en       = models.DateTimeField(null=True, blank=True)
    ruta_pdf         = models.TextField(null=True, blank=True)

    class Meta:
        db_table        = "reportes_mensuales"
        managed         = False
        unique_together = [("condominio", "periodo")]
