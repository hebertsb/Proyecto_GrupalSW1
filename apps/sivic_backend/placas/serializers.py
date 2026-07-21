from rest_framework import serializers
from .models import PlacaRegistrada, LecturaPlaca


class PlacaRegistradaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PlacaRegistrada
        fields = ["id", "condominio_id", "placa", "descripcion", "activa", "created_at", "updated_at"]
        read_only_fields = ["id", "condominio_id", "created_at", "updated_at"]


class LecturaPlacaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LecturaPlaca
        fields = [
            "id", "condominio_id", "camara_id", "placa_texto",
            "confianza_yolo", "confianza_ocr", "es_conocida",
            "placa_registrada_id", "imagen_url", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
