from django.db import models
from autenticacion.models import Usuario


class LogAuditoria(models.Model):
    log_id           = models.AutoField(primary_key=True)
    usuario          = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, db_column="usuario_id")
    accion           = models.TextField()
    tabla_afectada   = models.CharField(max_length=50, null=True, blank=True)
    timestamp_accion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logs_auditoria"
        managed  = False
        ordering = ["-timestamp_accion"]
