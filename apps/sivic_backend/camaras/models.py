from django.db import models
from condominios.models import Condominio


class Camara(models.Model):
    camara_id        = models.AutoField(primary_key=True)
    condominio       = models.ForeignKey(Condominio, on_delete=models.CASCADE, db_column="condominio_id", related_name="camaras")
    nombre_ubicacion = models.CharField(max_length=100)
    rtsp_url         = models.TextField()
    is_active        = models.BooleanField(default=True)

    class Meta:
        db_table = "camaras"
        managed  = False

    def __str__(self):
        return self.nombre_ubicacion


class ZonaRoi(models.Model):
    TIPO_CHOICES = [
        ("parqueo",              "Parqueo"),
        ("jardin",               "Jardín"),
        ("area_comun",           "Área Común"),
        ("zona_prohibida",       "Zona Prohibida"),
        ("horario_restringido",  "Horario Restringido (piscina/quinchos)"),
        ("perimetro",            "Perímetro del condominio"),
    ]

    roi_id               = models.AutoField(primary_key=True)
    camara               = models.ForeignKey(Camara, on_delete=models.CASCADE, db_column="camara_id", related_name="zonas_roi")
    poligono_coordenadas = models.JSONField()
    tipo_zona            = models.CharField(max_length=50, choices=TIPO_CHOICES)

    class Meta:
        db_table = "zonas_roi"
        managed  = False
