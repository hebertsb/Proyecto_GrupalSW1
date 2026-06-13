from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from autenticacion.permisos import EsAdmin
from .models import Plan, Condominio, Suscripcion
from .serializers import PlanSerializer, CondominioSerializer, SuscripcionSerializer


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset   = Plan.objects.prefetch_related("funcionalidades").all()
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]


class CondominioViewSet(viewsets.ModelViewSet):
    queryset   = Condominio.objects.all()
    serializer_class = CondominioSerializer
    permission_classes = [EsAdmin]


class SuscripcionViewSet(viewsets.ModelViewSet):
    queryset   = Suscripcion.objects.select_related("plan", "condominio").all()
    serializer_class = SuscripcionSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        condominio_id = self.request.query_params.get("condominio")
        if condominio_id:
            qs = qs.filter(condominio_id=condominio_id)
        return qs
