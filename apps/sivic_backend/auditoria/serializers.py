from rest_framework import serializers
from .models import LogAuditoria


class LogAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)

    class Meta:
        model  = LogAuditoria
        fields = ["log_id", "usuario", "usuario_nombre", "accion", "tabla_afectada", "timestamp_accion"]
