import os
import logging

# Silenciar ConnectionResetError de Windows al cerrar streams MJPEG
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Debe estar ANTES de cualquier import de Django o de la app
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from django.core.asgi import get_asgi_application

# Inicializar Django completamente antes de importar consumers/routing
django_asgi = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
import notificaciones.routing

application = ProtocolTypeRouter({
    "http": django_asgi,
    "websocket": URLRouter(notificaciones.routing.websocket_urlpatterns),
})
