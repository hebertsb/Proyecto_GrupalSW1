from rest_framework import serializers
from .models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    evento_tipo    = serializers.CharField(source="evento.regla.nombre_regla", read_only=True)

    class Meta:
        model  = Notificacion
        fields = [
            "notificacion_id", "evento", "evento_tipo",
            "usuario", "usuario_nombre",
            "titulo", "cuerpo", "estado", "created_at",
        ]
        read_only_fields = ["notificacion_id", "created_at"]
