from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from autenticacion.permisos import EsAdmin
from .models import Camara, ZonaRoi
from .serializers import CamaraSerializer, ZonaRoiSerializer


class CamaraViewSet(viewsets.ModelViewSet):
    """US-04: CRUD cámaras (admin). US-11: lista activas (guardia)."""
    serializer_class   = CamaraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Camara.objects.prefetch_related("zonas_roi").all()
        condominio_id = self.request.query_params.get("condominio")
        if condominio_id:
            qs = qs.filter(condominio_id=condominio_id)
        solo_activas = self.request.query_params.get("activas")
        if solo_activas:
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [IsAuthenticated()]


class ZonaRoiViewSet(viewsets.ModelViewSet):
    """US-03: Definir regiones de interés (ROI) por cámara."""
    serializer_class   = ZonaRoiSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = ZonaRoi.objects.select_related("camara").all()
        camara_id = self.request.query_params.get("camara")
        if camara_id:
            qs = qs.filter(camara_id=camara_id)
        return qs
