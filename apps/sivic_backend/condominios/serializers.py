from rest_framework import serializers
from .models import Plan, PlanFuncionalidad, Condominio, Suscripcion


class PlanFuncionalidadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PlanFuncionalidad
        fields = ["funcionalidad"]


class PlanSerializer(serializers.ModelSerializer):
    funcionalidades = PlanFuncionalidadSerializer(many=True, read_only=True)

    class Meta:
        model  = Plan
        fields = ["plan_id", "nombre", "precio_mensual", "funcionalidades"]


class CondominioSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Condominio
        fields = ["condominio_id", "nombre", "ubicacion"]


class SuscripcionSerializer(serializers.ModelSerializer):
    plan_nombre       = serializers.CharField(source="plan.nombre",       read_only=True)
    condominio_nombre = serializers.CharField(source="condominio.nombre", read_only=True)

    class Meta:
        model  = Suscripcion
        fields = [
            "suscripcion_id", "condominio", "condominio_nombre",
            "plan", "plan_nombre",
            "fecha_inicio", "is_activo",
            "stripe_estado", "periodo_actual_fin",
        ]
