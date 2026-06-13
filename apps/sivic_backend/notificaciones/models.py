from django.db import models
from autenticacion.models import Usuario
from eventos.models import Evento


class Notificacion(models.Model):
    ESTADO_CHOICES = [
        ("enviada",  "Enviada"),
        ("leida",    "Leída"),
        ("fallida",  "Fallida"),
    ]

    notificacion_id = models.AutoField(primary_key=True)
    evento          = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, db_column="evento_id", related_name="notificaciones")
    usuario         = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column="usuario_id", related_name="notificaciones")
    titulo          = models.TextField()
    cuerpo          = models.TextField(null=True, blank=True)
    token_fcm       = models.TextField(null=True, blank=True)
    estado          = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="enviada")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notificaciones"
        managed  = False
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titulo} → {self.usuario.nombre}"
