from rest_framework import serializers
from .models import PlacaRegistrada, LecturaPlaca


class PlacaRegistradaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="placa_id", read_only=True)

    class Meta:
        model  = PlacaRegistrada
        fields = ["id", "condominio_id", "placa", "descripcion", "activa", "created_at"]
        read_only_fields = ["id", "condominio_id", "created_at"]


class LecturaPlacaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LecturaPlaca
        fields = ["lectura_id", "camara_id", "placa_leida", "confianza", "es_conocida", "condominio_id", "timestamp"]
        read_only_fields = ["lectura_id", "timestamp"]
