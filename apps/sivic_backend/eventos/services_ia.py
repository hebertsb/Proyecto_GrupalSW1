"""
Servicio que recibe la detección del modelo YOLO, persiste el evento
y dispara la notificación push guardando el registro en BD.
"""
from camaras.models import Camara
from reglas.models import ReglaInfraccion
from .models import Evento


def registrar_deteccion(camara_id: int, regla_id: int, confianza: float, imagen_path: str = "") -> Evento:
    camara = Camara.objects.get(camara_id=camara_id)
    regla  = ReglaInfraccion.objects.get(regla_id=regla_id)

    evento = Evento.objects.create(
        camara                = camara,
        regla                 = regla,
        confianza_ia          = confianza,
        imagen_evidencia_path = imagen_path,
        estado                = "pendiente",
    )
    return evento


def notificar_guardias(evento: Evento, guardias: list[dict]):
    """
    Envía push a cada guardia y guarda registro en tabla notificaciones.
    guardias: lista de dict {"usuario_id": int, "token_fcm": str}
    """
    from autenticacion.models import Usuario
    from notificaciones.models import Notificacion
    from notificaciones.services_push import send_token

    regla_nombre  = evento.regla.nombre_regla if evento.regla else "Infracción"
    camara_nombre = evento.camara.nombre_ubicacion if evento.camara else "Cámara"
    titulo = f"Alerta: {regla_nombre}"
    cuerpo = f"Detectado en {camara_nombre}. Confianza: {evento.confianza_ia:.0%}"

    for guardia in guardias:
        usuario_id = guardia.get("usuario_id")
        token      = guardia.get("token_fcm", "")
        estado_envio = "enviada"

        try:
            if token:
                send_token(
                    token = token,
                    title = titulo,
                    body  = cuerpo,
                    data  = {
                        "evento_id": str(evento.evento_id),
                        "camara_id": str(evento.camara_id),
                        "tipo":      regla_nombre,
                    },
                )
        except Exception as e:
            print(f"Error FCM usuario {usuario_id}: {e}")
            estado_envio = "fallida"

        # Siempre guarda registro, éxito o fallo
        try:
            usuario = Usuario.objects.get(usuario_id=usuario_id)
            Notificacion.objects.create(
                evento    = evento,
                usuario   = usuario,
                titulo    = titulo,
                cuerpo    = cuerpo,
                token_fcm = token,
                estado    = estado_envio,
            )
        except Usuario.DoesNotExist:
            print(f"Usuario {usuario_id} no encontrado para guardar notificación")
