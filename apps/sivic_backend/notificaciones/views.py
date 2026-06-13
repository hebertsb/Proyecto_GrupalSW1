from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from autenticacion.permisos import EsAdmin
from .models import Notificacion
from .serializers import NotificacionSerializer
from .services_push import send_token
from .services_email import send_email


class NotificacionViewSet(viewsets.ReadOnlyModelViewSet):
    """Historial de notificaciones. Guardia ve las suyas; admin ve todas."""
    serializer_class   = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        qs = Notificacion.objects.select_related("usuario", "evento__regla").all()
        if getattr(usuario, "rol", None) != "admin":
            qs = qs.filter(usuario=usuario)
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    @action(detail=True, methods=["patch"], url_path="leer")
    def marcar_leida(self, request, pk=None):
        """Guardia marca la notificación como leída."""
        notif = self.get_object()
        if notif.usuario != request.user and getattr(request.user, "rol", None) != "admin":
            return Response({"error": "Sin permiso"}, status=status.HTTP_403_FORBIDDEN)
        notif.estado = "leida"
        notif.save(update_fields=["estado"])
        return Response(NotificacionSerializer(notif).data)


@api_view(["POST"])
@permission_classes([EsAdmin])
def enviar_push(request):
    """Envía push manual a un token FCM (pruebas o alertas manuales)."""
    token = request.data.get("token")
    title = request.data.get("title", "Alerta SIVIC")
    body  = request.data.get("body", "")

    if not token:
        return Response({"error": "token requerido"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        send_token(token, title, body)
        return Response({"ok": True})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([EsAdmin])
def enviar_email(request):
    """Envía email manual via Resend."""
    to      = request.data.get("to")
    subject = request.data.get("subject", "Notificación SIVIC")
    html    = request.data.get("html", "")

    if not to:
        return Response({"error": "to requerido"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        send_email(to, subject, html)
        return Response({"ok": True})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
