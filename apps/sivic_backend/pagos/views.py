import logging
import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from autenticacion.permisos import EsAdmin
from condominios.models import Condominio, Plan, Suscripcion
from .models import Pago, EventoWebhookStripe, ReporteMensual
from .serializers import PagoSerializer, ReporteMensualSerializer, SuscripcionEstadoSerializer
from . import services_stripe as stripe_svc

logger = logging.getLogger(__name__)


class CrearCheckoutView(APIView):
    """Crea una sesión de Stripe Checkout y devuelve la URL de pago."""
    permission_classes = [EsAdmin]

    def post(self, request):
        condominio_id   = request.data.get("condominio_id")
        plan_id         = request.data.get("plan_id")
        url_exito       = request.data.get("url_exito")
        url_cancelacion = request.data.get("url_cancelacion")

        if not all([condominio_id, plan_id, url_exito, url_cancelacion]):
            return Response(
                {"error": "Se requieren: condominio_id, plan_id, url_exito, url_cancelacion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            condominio = Condominio.objects.get(pk=condominio_id)
            plan       = Plan.objects.get(pk=plan_id)
        except (Condominio.DoesNotExist, Plan.DoesNotExist):
            return Response(
                {"error": "Condominio o plan no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not plan.stripe_precio_id:
            return Response(
                {"error": "Este plan no tiene un precio configurado en Stripe."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sesion = stripe_svc.crear_checkout_session(condominio, plan, url_exito, url_cancelacion)
            return Response({"url_checkout": sesion.url})
        except stripe.error.StripeError as e:
            logger.error("Error de Stripe al crear checkout: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


@csrf_exempt
@require_POST
def webhook_stripe(request):
    """
    Recibe eventos de Stripe. Sin autenticación JWT — la seguridad
    la garantiza la verificación de firma con STRIPE_WEBHOOK_SECRET.
    """
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        evento = stripe_svc.verificar_webhook(request.body, sig_header)
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook de Stripe rechazado: firma inválida")
        return HttpResponse(status=400)

    evento_id = evento["id"]

    # Idempotencia: si el evento ya fue procesado, responder 200 sin hacer nada
    if EventoWebhookStripe.objects.filter(stripe_evento_id=evento_id).exists():
        return HttpResponse(status=200)

    EventoWebhookStripe.objects.create(
        stripe_evento_id=evento_id,
        tipo_evento=evento["type"],
        datos_evento=dict(evento),
    )

    try:
        _procesar_evento(evento)
    except Exception:
        logger.exception("Error al procesar webhook %s", evento_id)
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def _procesar_evento(evento):
    import json as _json
    # Normalizar evento (stripe-python v5 usa objetos tipados)
    if not isinstance(evento, dict):
        evento = _json.loads(str(evento))
    tipo  = evento["type"]
    datos = evento["data"]["object"]

    if tipo == "checkout.session.completed":
        sub_completo = stripe.Subscription.retrieve(datos["subscription"])
        meta = datos.get("metadata") or {}
        stripe_svc.sincronizar_suscripcion(
            sub_completo,
            condominio_id=meta.get("condominio_id"),
            plan_id=meta.get("plan_id"),
        )

    elif tipo in ("customer.subscription.updated", "customer.subscription.deleted"):
        stripe_svc.sincronizar_suscripcion(datos)

    elif tipo == "invoice.paid":
        suscripcion = Suscripcion.objects.filter(
            stripe_suscripcion_id=datos.get("subscription")
        ).first()
        if suscripcion:
            stripe_svc.registrar_pago(datos, suscripcion)

    elif tipo == "invoice.payment_failed":
        suscripcion = Suscripcion.objects.filter(
            stripe_suscripcion_id=datos.get("subscription")
        ).first()
        if suscripcion and suscripcion.stripe_estado == "active":
            suscripcion.stripe_estado = "past_due"
            suscripcion.save(update_fields=["stripe_estado"])


class PagoListView(generics.ListAPIView):
    """Lista el historial de pagos. Filtrar por ?condominio=<id>."""
    serializer_class   = PagoSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = Pago.objects.select_related("suscripcion__plan", "condominio").order_by("-creado_en")
        condominio_id = self.request.query_params.get("condominio")
        if condominio_id:
            qs = qs.filter(condominio_id=condominio_id)
        return qs


class ReporteMensualListView(generics.ListAPIView):
    """Lista los reportes mensuales (plan Premium). Filtrar por ?condominio=<id>."""
    serializer_class   = ReporteMensualSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = ReporteMensual.objects.select_related("condominio").order_by("-periodo")
        condominio_id = self.request.query_params.get("condominio")
        if condominio_id:
            qs = qs.filter(condominio_id=condominio_id)
        return qs


class SuscripcionEstadoView(APIView):
    """Estado actual de suscripción de un condominio."""
    permission_classes = [EsAdmin]

    def get(self, request, condominio_id):
        suscripcion = (
            Suscripcion.objects
            .filter(condominio_id=condominio_id, is_activo=True)
            .select_related("plan")
            .first()
        )
        if suscripcion is None:
            return Response({"activo": False, "mensaje": "Sin suscripción activa."})
        return Response(SuscripcionEstadoSerializer(suscripcion).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def sincronizar_condominio(request):
    """
    Recupera la suscripción activa de Stripe para un condominio y actualiza la BD.
    Body: { "condominio_id": 5 }
    Uso superadmin: para condominios con stripe_cliente_id pero suscripcion sin datos.
    """
    from condominios.models import Condominio as Cond
    condominio_id = request.data.get("condominio_id")
    if not condominio_id:
        return Response({"error": "condominio_id requerido"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        condominio = Cond.objects.get(pk=condominio_id)
    except Cond.DoesNotExist:
        return Response({"error": "Condominio no encontrado"}, status=404)

    if not condominio.stripe_cliente_id:
        return Response({"error": "El condominio no tiene cliente de Stripe registrado"}, status=400)

    import json as _json

    subs = stripe.Subscription.list(customer=condominio.stripe_cliente_id, limit=1, status="all")
    if not subs.data:
        return Response({"error": "Sin suscripciones en Stripe para este condominio"}, status=404)

    # Normalizar a dict (stripe-python v5 usa objetos tipados)
    sub_dict = _json.loads(str(subs.data[0]))
    items    = sub_dict.get("items", {}).get("data", [])
    price_id = items[0].get("price", {}).get("id") if items else None
    plan_id  = None
    if price_id:
        plan = Plan.objects.filter(stripe_precio_id=price_id).first()
        if plan:
            plan_id = plan.plan_id

    suscripcion = stripe_svc.sincronizar_suscripcion(
        sub_dict,
        condominio_id=str(condominio_id),
        plan_id=str(plan_id) if plan_id else None,
    )
    if suscripcion:
        return Response({"ok": True, "stripe_estado": suscripcion.stripe_estado,
                         "periodo_fin": str(suscripcion.periodo_actual_fin)})
    return Response({"error": "No se pudo sincronizar"}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def confirmar_sesion(request):
    """
    Confirma una sesión de Stripe Checkout ya completada.
    Llamado desde el frontend cuando Stripe redirige a ?pago=ok&session_id=cs_xxx.
    No requiere JWT: la sesión misma es la prueba del pago.
    """
    session_id = request.data.get("session_id", "").strip()
    if not session_id:
        return Response({"error": "session_id requerido"}, status=status.HTTP_400_BAD_REQUEST)

    import json as _json

    try:
        sesion = stripe.checkout.Session.retrieve(
            session_id,
            expand=["subscription"],
        )
    except stripe.error.StripeError as e:
        return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

    # Normalizar a dict para acceso consistente
    sesion_dict = _json.loads(str(sesion))

    if sesion_dict.get("payment_status") not in ("paid", "no_payment_required"):
        return Response({"ok": False, "estado": sesion_dict.get("payment_status")})

    meta          = sesion_dict.get("metadata") or {}
    condominio_id = meta.get("condominio_id")
    plan_id       = meta.get("plan_id")
    sub_obj       = sesion_dict.get("subscription")

    if sub_obj is None:
        return Response({"error": "La sesión no tiene suscripción asociada"}, status=400)

    suscripcion = stripe_svc.sincronizar_suscripcion(sub_obj, condominio_id, plan_id)

    if suscripcion:
        return Response({"ok": True, "estado": suscripcion.stripe_estado})
    return Response({"ok": False, "error": "No se pudo sincronizar la suscripción"}, status=500)
