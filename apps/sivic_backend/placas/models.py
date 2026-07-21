from django.db import models


class PlacaRegistrada(models.Model):
    placa_id      = models.AutoField(primary_key=True, db_column='id')
    condominio_id = models.IntegerField()
    placa         = models.CharField(max_length=20)
    descripcion   = models.TextField(null=True, blank=True)
    activa        = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "placa_registrada"
        managed         = False
        unique_together = [("condominio_id", "placa")]

    def __str__(self):
        return self.placa


class LecturaPlaca(models.Model):
    lectura_id    = models.AutoField(primary_key=True, db_column='id')
    camara_id     = models.IntegerField(null=True)
    placa_leida   = models.CharField(max_length=20)
    confianza     = models.FloatField(null=True)
    es_conocida   = models.BooleanField(default=False)
    condominio_id = models.IntegerField()
    timestamp     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lectura_placa"
        managed  = False
