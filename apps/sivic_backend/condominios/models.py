from django.db import models


class Plan(models.Model):
    plan_id        = models.AutoField(primary_key=True)
    nombre         = models.CharField(max_length=20, unique=True)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "planes"
        managed  = False

    def __str__(self):
        return self.nombre


class PlanFuncionalidad(models.Model):
    plan          = models.ForeignKey(Plan, on_delete=models.CASCADE, db_column="plan_id", related_name="funcionalidades")
    funcionalidad = models.CharField(max_length=50)

    class Meta:
        db_table    = "plan_funcionalidades"
        managed     = False
        unique_together = [("plan", "funcionalidad")]


class Condominio(models.Model):
    condominio_id = models.AutoField(primary_key=True)
    nombre        = models.CharField(max_length=100)
    ubicacion     = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "condominio"
        managed  = False

    def __str__(self):
        return self.nombre


class Suscripcion(models.Model):
    suscripcion_id = models.AutoField(primary_key=True)
    condominio     = models.ForeignKey(Condominio, on_delete=models.CASCADE, db_column="condominio_id", related_name="suscripciones")
    plan           = models.ForeignKey(Plan, on_delete=models.PROTECT, db_column="plan_id")
    fecha_inicio   = models.DateField(auto_now_add=True)
    is_activo      = models.BooleanField(default=True)

    class Meta:
        db_table = "suscripciones"
        managed  = False
