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


class PlanoCondominio(models.Model):
    plano_id      = models.AutoField(primary_key=True)
    condominio    = models.ForeignKey(Condominio, on_delete=models.CASCADE, db_column="condominio_id", related_name="planos")
    nombre        = models.CharField(max_length=100)
    imagen_url    = models.TextField()
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "planos_condominio"
        managed  = False

    def __str__(self):
        return self.nombre


class PosicionCamara(models.Model):
    posicion_id = models.AutoField(primary_key=True)
    plano       = models.ForeignKey(PlanoCondominio, on_delete=models.CASCADE, db_column="plano_id", related_name="posiciones")
    camara      = models.ForeignKey(Camara, on_delete=models.CASCADE, db_column="camara_id", related_name="posiciones_plano")
    pos_x       = models.DecimalField(max_digits=5, decimal_places=4)
    pos_y       = models.DecimalField(max_digits=5, decimal_places=4)

    class Meta:
        db_table        = "posiciones_camaras"
        managed         = False
        unique_together = [("plano", "camara")]


class ImagenZona(models.Model):
    imagen_id  = models.AutoField(primary_key=True)
    posicion   = models.ForeignKey(PosicionCamara, on_delete=models.CASCADE, db_column="posicion_id", related_name="imagenes_zona")
    imagen_url = models.TextField()
    orden      = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "imagenes_zona"
        managed  = False
        ordering = ["orden", "created_at"]
