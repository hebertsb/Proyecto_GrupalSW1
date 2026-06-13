from rest_framework import viewsets
from autenticacion.permisos import EsAdmin
from .models import Dataset, DatasetEvento
from .serializers import DatasetSerializer, DatasetEventoSerializer


class DatasetViewSet(viewsets.ModelViewSet):
    queryset           = Dataset.objects.all()
    serializer_class   = DatasetSerializer
    permission_classes = [EsAdmin]


class DatasetEventoViewSet(viewsets.ModelViewSet):
    serializer_class   = DatasetEventoSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = DatasetEvento.objects.select_related("dataset", "evento").all()
        dataset_id = self.request.query_params.get("dataset")
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        return qs
