from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from autenticacion.permisos import EsAdmin, EsGuardia
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
        qs = Evento.objects.select_related("camara", "regla", "atendido_por").all()
        estado    = self.request.query_params.get("estado")
        camara_id = self.request.query_params.get("camara")
        if estado:
            qs = qs.filter(estado=estado)
        if camara_id:
            qs = qs.filter(camara_id=camara_id)
        return qs

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
