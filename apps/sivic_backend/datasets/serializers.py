from rest_framework import serializers
from .models import Dataset, DatasetEvento


class DatasetEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DatasetEvento
        fields = ["dataset", "evento", "etiqueta_correcta"]


class DatasetSerializer(serializers.ModelSerializer):
    total_eventos = serializers.SerializerMethodField()

    class Meta:
        model  = Dataset
        fields = ["dataset_id", "nombre", "version_modelo", "total_eventos"]

    def get_total_eventos(self, obj):
        return obj.items.count()
