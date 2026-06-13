from rest_framework import serializers
from .models import Camara, ZonaRoi


class ZonaRoiSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ZonaRoi
        fields = ["roi_id", "camara", "poligono_coordenadas", "tipo_zona"]


class CamaraSerializer(serializers.ModelSerializer):
    zonas_roi = ZonaRoiSerializer(many=True, read_only=True)

    class Meta:
        model  = Camara
        fields = ["camara_id", "condominio", "nombre_ubicacion", "rtsp_url", "is_active", "zonas_roi"]
