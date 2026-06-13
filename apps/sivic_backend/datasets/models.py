from django.db import models
from eventos.models import Evento


class Dataset(models.Model):
    dataset_id     = models.AutoField(primary_key=True)
    nombre         = models.CharField(max_length=50)
    version_modelo = models.CharField(max_length=20)

    class Meta:
        db_table = "datasets"
        managed  = False

    def __str__(self):
        return f"{self.nombre} v{self.version_modelo}"


class DatasetEvento(models.Model):
    dataset           = models.ForeignKey(Dataset, on_delete=models.CASCADE, db_column="dataset_id", related_name="items")
    evento            = models.ForeignKey(Evento, on_delete=models.CASCADE, db_column="evento_id")
    etiqueta_correcta = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table    = "dataset_eventos"
        managed     = False
        unique_together = [("dataset", "evento")]
