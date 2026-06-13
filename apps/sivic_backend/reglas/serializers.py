from rest_framework import serializers
from .models import ReglaInfraccion


class ReglaInfraccionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReglaInfraccion
        fields = ["regla_id", "nombre_regla", "descripcion"]
