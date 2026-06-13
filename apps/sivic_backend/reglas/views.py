from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from autenticacion.permisos import EsAdmin
from .models import ReglaInfraccion
from .serializers import ReglaInfraccionSerializer


class ReglaInfraccionViewSet(viewsets.ModelViewSet):
    """US-05: CRUD reglas de infracción (admin)."""
    queryset           = ReglaInfraccion.objects.all()
    serializer_class   = ReglaInfraccionSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [IsAuthenticated()]
