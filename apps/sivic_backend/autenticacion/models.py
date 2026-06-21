from django.db import models


class Usuario(models.Model):
    ROL_CHOICES = [("superadmin", "Super Admin"), ("admin", "Admin"), ("guardia", "Guardia")]

    usuario_id    = models.AutoField(primary_key=True)
    nombre        = models.CharField(max_length=100)
    email         = models.EmailField(max_length=100, unique=True)
    password_hash = models.TextField()
    rol           = models.CharField(max_length=20, choices=ROL_CHOICES)
    condominio    = models.ForeignKey(
        "condominios.Condominio",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="condominio_id",
        related_name="usuarios",
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios"
        managed  = False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f"{self.nombre} ({self.rol})"
