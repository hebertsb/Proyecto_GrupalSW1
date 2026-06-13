from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Usuario
        fields = ["usuario_id", "nombre", "email", "rol", "created_at"]


class RegistroSerializer(serializers.Serializer):
    nombre   = serializers.CharField(max_length=100)
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    rol      = serializers.ChoiceField(choices=["admin", "guardia"])
