from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from autenticacion.permisos import EsAdmin
from .models import LogAuditoria
from .serializers import LogAuditoriaSerializer


class LogAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """US-14: Consultar logs de auditoría (solo admin)."""
    serializer_class   = LogAuditoriaSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = LogAuditoria.objects.select_related("usuario").all()
        usuario_id     = self.request.query_params.get("usuario")
        tabla_afectada = self.request.query_params.get("tabla")
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        if tabla_afectada:
            qs = qs.filter(tabla_afectada=tabla_afectada)
        return qs
