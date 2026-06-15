from rest_framework import serializers
from .models import Camara, ZonaRoi, PlanoCondominio, PosicionCamara, ImagenZona


class ZonaRoiSerializer(serializers.ModelSerializer):
    # CharField libre para no restringir los tipos a los choices del modelo
    tipo_zona = serializers.CharField(max_length=50)

    class Meta:
        model  = ZonaRoi
        fields = ["roi_id", "camara", "poligono_coordenadas", "tipo_zona"]


class CamaraSerializer(serializers.ModelSerializer):
    zonas_roi = ZonaRoiSerializer(many=True, read_only=True)

    class Meta:
        model  = Camara
        fields = ["camara_id", "condominio", "nombre_ubicacion", "rtsp_url", "is_active", "zonas_roi"]


class ImagenZonaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ImagenZona
        fields = ["imagen_id", "posicion", "imagen_url", "orden", "created_at"]


class PosicionCamaraSerializer(serializers.ModelSerializer):
    nombre_camara = serializers.CharField(source="camara.nombre_ubicacion", read_only=True)
    imagenes_zona = ImagenZonaSerializer(many=True, read_only=True)

    class Meta:
        model  = PosicionCamara
        fields = ["posicion_id", "plano", "camara", "nombre_camara", "pos_x", "pos_y", "imagenes_zona"]


class PlanoCondominioSerializer(serializers.ModelSerializer):
    posiciones = PosicionCamaraSerializer(many=True, read_only=True)

    class Meta:
        model  = PlanoCondominio
        fields = ["plano_id", "condominio", "nombre", "imagen_url", "created_at", "posiciones"]
