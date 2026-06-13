from django.db import models
from camaras.models import Camara
from reglas.models import ReglaInfraccion
from autenticacion.models import Usuario


class Evento(models.Model):
    ESTADO_CHOICES = [
        ("pendiente",    "Pendiente"),
        ("en_atencion",  "En Atención"),
        ("resuelto",     "Resuelto"),
        ("falsa_alarma", "Falsa Alarma"),
    ]

    evento_id             = models.AutoField(primary_key=True)
    camara                = models.ForeignKey(Camara, on_delete=models.SET_NULL, null=True, db_column="camara_id", related_name="eventos")
    regla                 = models.ForeignKey(ReglaInfraccion, on_delete=models.SET_NULL, null=True, db_column="regla_id")
    timestamp_deteccion   = models.DateTimeField(auto_now_add=True)
    confianza_ia          = models.FloatField()
    estado                = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    imagen_evidencia_path = models.TextField(null=True, blank=True)
    resolucion            = models.TextField(null=True, blank=True)
    atendido_por          = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, db_column="atendido_por")
    tiempo_respuesta      = models.DurationField(null=True, blank=True)

    class Meta:
        db_table = "eventos"
        managed  = False
        ordering = ["-timestamp_deteccion"]
