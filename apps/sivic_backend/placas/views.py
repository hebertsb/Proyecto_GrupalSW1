from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from camaras.models import Camara
from autenticacion.permisos import EsAdmin, filtrar_por_condominio
from .models import PlacaRegistrada, LecturaPlaca
from .serializers import PlacaRegistradaSerializer, LecturaPlacaSerializer


class PlacaRegistradaViewSet(viewsets.ModelViewSet):
    serializer_class = PlacaRegistradaSerializer

    def get_queryset(self):
        qs = PlacaRegistrada.objects.all().order_by("-created_at")
        return filtrar_por_condominio(qs, self.request)

    def get_permissions(self):
        if self.action in ("list", "retrieve", "verificar"):
            return [AllowAny()]
        return [EsAdmin()]

    def perform_create(self, serializer):
        cid = getattr(self.request.user, "condominio_id", None)
        serializer.save(condominio_id=cid)

    @action(detail=False, methods=["post"], url_path="verificar")
    def verificar(self, request):
        """
        Llamado por el servicio FastAPI (interno).
        Recibe: { placa, camara_id, confianza }
        Registra lectura y retorna si la placa es conocida.
        """
        placa_texto = request.data.get("placa", "").strip().upper()
        camara_id   = request.data.get("camara_id")
        confianza   = float(request.data.get("confianza", 0.0))

        if not placa_texto or not camara_id:
            return Response({"error": "placa y camara_id requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            camara = Camara.objects.get(camara_id=camara_id)
            condominio_id = camara.condominio_id
        except Camara.DoesNotExist:
            return Response({"error": "camara no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        es_conocida = PlacaRegistrada.objects.filter(
            condominio_id=condominio_id,
            placa=placa_texto,
            activa=True,
        ).exists()

        LecturaPlaca.objects.create(
            camara_id=camara_id,
            placa_leida=placa_texto,
            confianza=confianza,
            es_conocida=es_conocida,
            condominio_id=condominio_id,
        )

        if not es_conocida:
            _generar_alerta_placa(camara, placa_texto, confianza)

        return Response({
            "placa":       placa_texto,
            "es_conocida": es_conocida,
            "condominio_id": condominio_id,
        })


def _generar_alerta_placa(camara, placa_texto: str, confianza: float):
    from reglas.models import ReglaInfraccion
    from eventos.models import Evento
    from autenticacion.models import Usuario
    from notificaciones.models import Notificacion
    from notificaciones.services_push import send_token

    try:
        regla = ReglaInfraccion.objects.filter(nombre_regla__icontains="placa").first()
        if not regla:
            regla = ReglaInfraccion.objects.first()
        if not regla:
            return

        evento = Evento.objects.create(
            camara=camara,
            regla=regla,
            confianza_ia=confianza,
            estado="pendiente",
        )

        guardias = Usuario.objects.filter(
            condominio_id=camara.condominio_id,
            rol__in=("guardia", "admin"),
        ).exclude(fcm_token=None).exclude(fcm_token="")

        titulo = "Alerta: Placa no registrada"
        cuerpo = f"Vehículo con placa {placa_texto} detectado en {camara.nombre_ubicacion}"

        for guardia in guardias:
            try:
                send_token(
                    token=guardia.fcm_token,
                    title=titulo,
                    body=cuerpo,
                    data={"evento_id": str(evento.evento_id), "placa": placa_texto},
                )
                estado_envio = "enviada"
            except Exception:
                estado_envio = "fallida"

            Notificacion.objects.create(
                evento=evento,
                usuario=guardia,
                titulo=titulo,
                cuerpo=cuerpo,
                token_fcm=guardia.fcm_token,
                estado=estado_envio,
            )
    except Exception as e:
        print(f"[SIVIC] Error generando alerta placa: {e}")


class LecturaPlacaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LecturaPlacaSerializer

    def get_queryset(self):
        qs = LecturaPlaca.objects.all().order_by("-timestamp")
        return filtrar_por_condominio(qs, self.request)

    def get_permissions(self):
        return [IsAuthenticated()]
