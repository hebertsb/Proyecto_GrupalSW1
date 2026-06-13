from django.db import models


class ReglaInfraccion(models.Model):
    regla_id     = models.AutoField(primary_key=True)
    nombre_regla = models.CharField(max_length=50, unique=True)
    descripcion  = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "reglas_infraccion"
        managed  = False

    def __str__(self):
        return self.nombre_regla
