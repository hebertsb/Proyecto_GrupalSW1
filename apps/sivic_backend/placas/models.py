import uuid
from django.db import models


class PlacaRegistrada(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    condominio_id = models.IntegerField()
    placa         = models.CharField(max_length=10)
    descripcion   = models.TextField(null=True, blank=True)
    activa        = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "placa_registrada"
        managed         = False
        unique_together = [("condominio_id", "placa")]

    def __str__(self):
        return self.placa


class LecturaPlaca(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    condominio_id       = models.IntegerField()
    camara_id           = models.IntegerField()
    placa_texto         = models.CharField(max_length=10, null=True, blank=True)
    confianza_yolo      = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    confianza_ocr       = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    es_conocida         = models.BooleanField(null=True)
    placa_registrada_id = models.UUIDField(null=True, blank=True)
    imagen_url          = models.TextField(null=True, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lectura_placa"
        managed  = False
