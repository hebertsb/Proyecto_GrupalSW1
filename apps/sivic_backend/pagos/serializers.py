from rest_framework import serializers
from condominios.models import Suscripcion
from .models import Pago, ReporteMensual


class PagoSerializer(serializers.ModelSerializer):
    condominio_nombre = serializers.CharField(source="condominio.nombre", read_only=True)
    plan_nombre       = serializers.CharField(source="suscripcion.plan.nombre", read_only=True)

    class Meta:
        model  = Pago
        fields = [
            "pago_id", "condominio", "condominio_nombre",
            "suscripcion", "plan_nombre",
            "stripe_factura_id", "stripe_intento_pago_id",
            "monto", "moneda", "estado",
            "periodo_inicio", "periodo_fin",
            "creado_en", "pagado_en",
        ]


class ReporteMensualSerializer(serializers.ModelSerializer):
    condominio_nombre = serializers.CharField(source="condominio.nombre", read_only=True)

    class Meta:
        model  = ReporteMensual
        fields = [
            "reporte_id", "condominio", "condominio_nombre",
            "periodo", "total_eventos",
            "eventos_parqueo", "eventos_mascotas", "eventos_acceso",
            "generado_en", "enviado_en", "ruta_pdf",
        ]


class SuscripcionEstadoSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)

    class Meta:
        model  = Suscripcion
        fields = [
            "suscripcion_id", "plan", "plan_nombre",
            "stripe_estado", "is_activo",
            "fecha_inicio", "fecha_fin",
            "periodo_actual_inicio", "periodo_actual_fin",
            "cancelar_al_vencer",
        ]
