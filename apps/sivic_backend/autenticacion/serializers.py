from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    condominio_nombre = serializers.CharField(source="condominio.nombre", read_only=True, default=None)

    class Meta:
        model  = Usuario
        fields = ["usuario_id", "nombre", "email", "rol", "condominio", "condominio_nombre", "created_at"]


class RegistroSerializer(serializers.Serializer):
    nombre   = serializers.CharField(max_length=100)
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    rol      = serializers.ChoiceField(choices=["admin", "guardia"])
