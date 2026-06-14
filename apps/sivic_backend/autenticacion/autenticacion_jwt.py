import jwt
import os
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Usuario


class AutenticacionJWT(BaseAuthentication):
    """Valida el Bearer token JWT en cada request."""

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        encabezado = request.headers.get("Authorization", "")
        if encabezado.startswith("Bearer "):
            token = encabezado.split(" ")[1]
        else:
            # Query-param fallback para <img src="...?token="> y stream MJPEG
            token = request.GET.get("token", "")
            if not token:
                return None
        try:
            payload = jwt.decode(
                token,
                os.environ.get("SECRET_KEY", ""),
                algorithms=["HS256"],
            )
            usuario = Usuario.objects.get(usuario_id=payload["usuario_id"])
            return (usuario, token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expirado")
        except (jwt.InvalidTokenError, Usuario.DoesNotExist):
            raise AuthenticationFailed("Token inválido")
