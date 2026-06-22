import requests as req_ext

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from autenticacion.permisos import EsAdmin, EsGuardia, filtrar_por_condominio
from .models import Evento
from .serializers import EventoSerializer, ActualizarEstadoSerializer, InferenciaIASerializer
from .services_ia import registrar_deteccion, notificar_guardias


@extend_schema_view(
    list=extend_schema(
        tags=["Eventos"],
        summary="Listar eventos / alertas",
        description="Historial de detecciones IA. Filtros: `?estado=pendiente`, `?camara=<id>`.",
        parameters=[
            OpenApiParameter("estado",  description="pendiente | en_atencion | resuelto | falsa_alarma"),
            OpenApiParameter("camara",  description="ID de cámara"),
        ],
    ),
    retrieve=extend_schema(
        tags=["Eventos"],
        summary="Detalle de evento",
    ),
    partial_update=extend_schema(
        tags=["Eventos"],
        summary="Actualizar evento",
        description="Uso interno (preferir endpoint /estado/).",
    ),
)
class EventoViewSet(viewsets.ModelViewSet):
    """
    Historial de alertas de infracción detectadas por la IA.
    Guardia puede listar y actualizar estado; admin tiene acceso total.
    """
    serializer_class   = EventoSerializer
    permission_classes = [EsGuardia]
    http_method_names  = ["get", "patch", "head", "options"]

    def get_queryset(self):
        from django.utils import timezone
        import datetime
        qs = Evento.objects.select_related("camara", "regla", "atendido_por").all()
        qs = filtrar_por_condominio(qs, self.request, campo="camara__condominio_id")
        estado    = self.request.query_params.get("estado")
        camara_id = self.request.query_params.get("camara")
        dias      = int(self.request.query_params.get("dias", 7))
        if estado:
            qs = qs.filter(estado=estado)
        if camara_id:
            qs = qs.filter(camara_id=camara_id)
        desde = timezone.now() - datetime.timedelta(days=dias)
        return qs.filter(timestamp_deteccion__gte=desde)[:500]

    @extend_schema(
        tags=["Eventos"],
        summary="Actualizar estado de alerta",
        description=(
            "El guardia cambia el estado de una alerta.\n\n"
            "Estados válidos: `en_atencion` → `resuelto` o `falsa_alarma`.\n\n"
            "El trigger de BD calcula `tiempo_respuesta` automáticamente."
        ),
        request=ActualizarEstadoSerializer,
        responses={200: EventoSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="estado")
    def actualizar_estado(self, request, pk=None):
        evento = self.get_object()
        ser = ActualizarEstadoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        evento.estado     = ser.validated_data["estado"]
        evento.resolucion = ser.validated_data.get("resolucion", evento.resolucion)
        evento.atendido_por = request.user
        evento.save(update_fields=["estado", "resolucion", "atendido_por"])

        return Response(EventoSerializer(evento).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reportes_resumen(request):
    """
    GET /api/eventos/reportes/resumen/?dias=30&camara_id=1&regla=merodeo
    Datos agregados para el dashboard de reportes IA.
    Filtros opcionales: camara_id, regla (nombre_regla exacto), estado.
    """
    from django.db.models import Count, Avg
    from django.db.models.functions import TruncDate, ExtractHour
    from django.utils import timezone
    from camaras.models import Camara
    from reglas.models import ReglaInfraccion
    import datetime

    dias       = int(request.GET.get("dias", 30))
    camara_id  = request.GET.get("camara_id")
    regla_nom  = request.GET.get("regla")
    estado_fil = request.GET.get("estado")

    desde = timezone.now() - datetime.timedelta(days=dias)
    hoy   = timezone.now().date()

    qs = Evento.objects.filter(timestamp_deteccion__gte=desde)
    qs = filtrar_por_condominio(qs, request, campo="camara__condominio_id")
    if camara_id:
        qs = qs.filter(camara_id=camara_id)
    if regla_nom:
        qs = qs.filter(regla__nombre_regla=regla_nom)
    if estado_fil:
        qs = qs.filter(estado=estado_fil)

    total         = qs.count()
    total_hoy     = qs.filter(timestamp_deteccion__date=hoy).count()
    conf_prom_val = qs.aggregate(avg=Avg("confianza_ia"))["avg"] or 0

    por_camara = list(
        qs.values("camara__camara_id", "camara__nombre_ubicacion")
        .annotate(total=Count("evento_id"), confianza_prom=Avg("confianza_ia"))
        .order_by("-total")
    )
    por_regla = list(
        qs.values("regla__nombre_regla")
        .annotate(total=Count("evento_id"), confianza_prom=Avg("confianza_ia"))
        .order_by("-total")
    )
    por_hora = list(
        qs.annotate(hora=ExtractHour("timestamp_deteccion"))
        .values("hora").annotate(total=Count("evento_id")).order_by("hora")
    )
    por_dia = list(
        qs.annotate(fecha=TruncDate("timestamp_deteccion"))
        .values("fecha").annotate(total=Count("evento_id")).order_by("fecha")
    )
    por_estado = list(qs.values("estado").annotate(total=Count("evento_id")))

    camara_top = por_camara[0]["camara__nombre_ubicacion"] if por_camara else "—"
    regla_top  = por_regla[0]["regla__nombre_regla"]       if por_regla  else "—"

    # Listas para los selectores de filtro en el frontend
    camaras_qs = Camara.objects.filter(is_active=True)
    camaras_qs = filtrar_por_condominio(camaras_qs, request)
    camaras_disp = list(camaras_qs.values("camara_id", "nombre_ubicacion").order_by("nombre_ubicacion"))
    reglas_disp = list(
        ReglaInfraccion.objects.values_list("nombre_regla", flat=True).order_by("nombre_regla")
    )

    return Response({
        "kpis": {
            "total_eventos":      total,
            "eventos_hoy":        total_hoy,
            "confianza_promedio": round(conf_prom_val * 100, 1),
            "camara_top":         camara_top or "—",
            "regla_top":          regla_top  or "—",
            "dias":               dias,
            "filtros_activos": {
                "camara_id":  camara_id,
                "regla":      regla_nom,
                "estado":     estado_fil,
            },
        },
        "camaras_disponibles": [{"id": r["camara_id"], "nombre": r["nombre_ubicacion"]} for r in camaras_disp],
        "reglas_disponibles":  list(reglas_disp),
        "por_camara": [
            {"id": r["camara__camara_id"], "camara": r["camara__nombre_ubicacion"] or "Sin cámara",
             "total": r["total"], "confianza": round((r["confianza_prom"] or 0) * 100, 1)}
            for r in por_camara
        ],
        "por_regla": [
            {"regla": r["regla__nombre_regla"] or "Sin regla",
             "total": r["total"], "confianza": round((r["confianza_prom"] or 0) * 100, 1)}
            for r in por_regla
        ],
        "por_hora":   [{"hora": r["hora"], "total": r["total"]} for r in por_hora],
        "por_dia":    [{"fecha": r["fecha"].isoformat(), "total": r["total"]} for r in por_dia],
        "por_estado": [{"estado": r["estado"], "total": r["total"]} for r in por_estado],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def consulta_ia_reportes(request):
    """
    POST /api/eventos/reportes/consulta/
    Body: { "pregunta": "...", "datos": { resumen del reporte } }
    Llama a Groq (LLaMA-3) con los datos del reporte como contexto.
    La API key vive en .env — nunca se expone al browser.
    """
    from django.conf import settings as dj_settings
    import json

    pregunta = request.data.get("pregunta", "").strip()
    datos    = request.data.get("datos", {})

    if not pregunta:
        return Response({"error": "Campo 'pregunta' requerido"}, status=400)

    api_key = getattr(dj_settings, "GROQ_API_KEY", "")
    if not api_key:
        return Response({"error": "GROQ_API_KEY no configurado en .env"}, status=503)

    sistema = (
        "Eres un analista experto en seguridad de condominios. "
        "El usuario te pregunta sobre los reportes del sistema de vigilancia SIVIC. "
        "Responde en español, de forma clara y concisa (máx 3 oraciones). "
        "Menciona números concretos del reporte cuando sean relevantes. "
        "Si la pregunta no tiene relación con los datos, indícalo brevemente."
    )

    contexto = f"Datos del reporte:\n{json.dumps(datos, ensure_ascii=False, indent=2)}\n\nPregunta del usuario: {pregunta}"

    try:
        resp = req_ext.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system",  "content": sistema},
                    {"role": "user",    "content": contexto},
                ],
                "temperature": 0.4,
                "max_tokens":  300,
            },
            timeout=15,
        )
        if not resp.ok:
            return Response({"error": f"Groq {resp.status_code}: {resp.text[:400]}"}, status=502)
        respuesta = resp.json()["choices"][0]["message"]["content"].strip()
        return Response({"respuesta": respuesta, "pregunta": pregunta})
    except req_ext.exceptions.Timeout:
        return Response({"error": "Groq no respondió en 15s"}, status=504)
    except Exception as e:
        return Response({"error": str(e)}, status=502)


@extend_schema(
    tags=["Eventos"],
    summary="Webhook de inferencia IA",
    description=(
        "El servidor YOLO llama a este endpoint al detectar una infracción.\n\n"
        "Registra el evento automáticamente y envía notificación push a los guardias.\n\n"
        "**No requiere autenticación** (llamado desde el servidor IA interno).\n\n"
        "Payload de ejemplo:\n"
        "```json\n"
        '{"camara_id": 1, "regla_id": 2, "confianza": 0.92, "imagen_path": "frames/ev_001.jpg",\n'
        ' "guardias": [{"usuario_id": 3, "token_fcm": "fcm-token-del-guardia"}]}\n'
        "```"
    ),
    request=InferenciaIASerializer,
    responses={201: EventoSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def inferencia_ia(request):
    ser = InferenciaIASerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    try:
        evento = registrar_deteccion(
            camara_id   = d["camara_id"],
            regla_id    = d["regla_id"],
            confianza   = d["confianza"],
            imagen_path = d.get("imagen_path", ""),
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    guardias = request.data.get("guardias", [])
    if guardias:
        notificar_guardias(evento, guardias)

    return Response(EventoSerializer(evento).data, status=status.HTTP_201_CREATED)
