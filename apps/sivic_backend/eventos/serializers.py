import datetime
from rest_framework import serializers
from .models import Evento


class EventoSerializer(serializers.ModelSerializer):
    regla_nombre         = serializers.CharField(source="regla.nombre_regla", read_only=True)
    camara_nombre        = serializers.CharField(source="camara.nombre_ubicacion", read_only=True)
    atendido_nombre      = serializers.CharField(source="atendido_por.nombre", read_only=True)
    timestamp_deteccion  = serializers.SerializerMethodField()

    def get_timestamp_deteccion(self, obj):
        ts = obj.timestamp_deteccion
        if ts is None:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        return ts.isoformat().replace('+00:00', 'Z')

    class Meta:
        model  = Evento
        fields = [
            "evento_id", "camara", "camara_nombre", "regla", "regla_nombre",
            "timestamp_deteccion", "confianza_ia", "estado",
            "imagen_evidencia_path", "resolucion",
            "atendido_por", "atendido_nombre", "tiempo_respuesta",
        ]
        read_only_fields = ["evento_id", "timestamp_deteccion", "tiempo_respuesta"]


class ActualizarEstadoSerializer(serializers.Serializer):
    estado     = serializers.ChoiceField(choices=["en_atencion", "resuelto", "falsa_alarma"])
    resolucion = serializers.CharField(required=False, allow_blank=True)


class InferenciaIASerializer(serializers.Serializer):
    """Payload que envía el servidor de IA al detectar una infracción."""
    camara_id   = serializers.IntegerField()
    regla_id    = serializers.IntegerField()
    confianza   = serializers.FloatField(min_value=0.0, max_value=1.0)
    imagen_path = serializers.CharField(required=False, allow_blank=True)
