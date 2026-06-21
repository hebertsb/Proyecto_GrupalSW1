import stripe
from datetime import date, datetime
from django.conf import settings
from django.utils.timezone import make_aware

stripe.api_key = settings.STRIPE_SECRET_KEY


def _unix_a_fecha(ts):
    """Convierte timestamp Unix a date. Retorna None si ts es None."""
    return date.fromtimestamp(ts) if ts else None


def _unix_a_datetime(ts):
    """Convierte timestamp Unix a datetime con timezone. Retorna None si ts es None."""
    return make_aware(datetime.fromtimestamp(ts)) if ts else None


def obtener_o_crear_cliente(condominio):
    """Obtiene el stripe_cliente_id del condominio o crea uno nuevo en Stripe."""
    if condominio.stripe_cliente_id:
        return condominio.stripe_cliente_id
    cliente = stripe.Customer.create(
        name=condominio.nombre,
        metadata={"condominio_id": str(condominio.condominio_id)},
    )
    condominio.stripe_cliente_id = cliente.id
    condominio.save(update_fields=["stripe_cliente_id"])
    return cliente.id


def crear_checkout_session(condominio, plan, url_exito, url_cancelacion):
    """Crea una sesión de Stripe Checkout para suscribirse a un plan."""
    cliente_id = obtener_o_crear_cliente(condominio)
    return stripe.checkout.Session.create(
        customer=cliente_id,
        mode="subscription",
        line_items=[{"price": plan.stripe_precio_id, "quantity": 1}],
        success_url=url_exito,
        cancel_url=url_cancelacion,
        metadata={
            "condominio_id": str(condominio.condominio_id),
            "plan_id":       str(plan.plan_id),
        },
    )


def verificar_webhook(payload, sig_header):
    """Verifica la firma del webhook y retorna el evento de Stripe."""
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )


def sincronizar_suscripcion(sub_datos, condominio_id=None, plan_id=None):
    """
    Crea o actualiza la Suscripcion local desde los datos de un Subscription de Stripe.
    El trigger trg_sincronizar_activo en la BD actualiza is_activo automáticamente.
    """
    import json

    # stripe-python v5+ usa objetos tipados, no dicts. Normalizar.
    if not isinstance(sub_datos, dict):
        sub_datos = json.loads(str(sub_datos))

    from condominios.models import Suscripcion

    suscripcion = Suscripcion.objects.filter(
        stripe_suscripcion_id=sub_datos["id"]
    ).first()

    # Si el registro encontrado tiene un condominio_id incorrecto, corregirlo.
    if suscripcion is not None and condominio_id and suscripcion.condominio_id != int(condominio_id):
        suscripcion.condominio_id = int(condominio_id)

    if suscripcion is None and condominio_id:
        # Buscar el registro incomplete creado al momento del registro
        suscripcion = Suscripcion.objects.filter(
            condominio_id=int(condominio_id),
            stripe_suscripcion_id__isnull=True,
        ).first()

    if suscripcion is None:
        if condominio_id is None:
            return None
        suscripcion = Suscripcion(
            condominio_id=int(condominio_id),
            plan_id=int(plan_id),
        )

    # En Stripe API 2024-06+, current_period_* está en items.data[0], no en la raíz
    _items = sub_datos.get("items", {}).get("data", [])
    _item0 = _items[0] if _items else {}
    periodo_inicio = sub_datos.get("current_period_start") or _item0.get("current_period_start")
    periodo_fin    = sub_datos.get("current_period_end")   or _item0.get("current_period_end")

    suscripcion.stripe_suscripcion_id = sub_datos["id"]
    suscripcion.stripe_estado         = sub_datos["status"]
    suscripcion.fecha_fin             = _unix_a_fecha(periodo_fin)
    suscripcion.periodo_actual_inicio = _unix_a_fecha(periodo_inicio)
    suscripcion.periodo_actual_fin    = _unix_a_fecha(periodo_fin)
    suscripcion.cancelar_al_vencer    = sub_datos.get("cancel_at_period_end", False)
    suscripcion.save()
    return suscripcion


def registrar_pago(invoice_datos, suscripcion):
    """Crea un registro en la tabla pagos a partir de un Invoice de Stripe."""
    from .models import Pago

    transitions = invoice_datos.get("status_transitions") or {}
    Pago.objects.get_or_create(
        stripe_factura_id=invoice_datos["id"],
        defaults={
            "suscripcion_id":         suscripcion.suscripcion_id,
            "condominio_id":          suscripcion.condominio_id,
            "stripe_intento_pago_id": invoice_datos.get("payment_intent"),
            "monto":                  invoice_datos["amount_paid"] / 100,
            "moneda":                 invoice_datos["currency"],
            "estado":                 invoice_datos["status"],
            "periodo_inicio":         _unix_a_fecha(invoice_datos.get("period_start")),
            "periodo_fin":            _unix_a_fecha(invoice_datos.get("period_end")),
            "pagado_en":              _unix_a_datetime(transitions.get("paid_at")),
        },
    )
