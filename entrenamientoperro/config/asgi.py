import os
from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from api import app as fastapi_app # Importamos tu archivo de FastAPI

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Inicializamos la app de Django
django_app = get_asgi_application()

# Creamos la app principal ASGI
final_app = FastAPI()

# Redireccionamos: Todo lo que vaya a /api lo maneja FastAPI
final_app.mount("/api", fastapi_app)

# Todo lo demás lo maneja Django (vistas, panel de administración, etc.)
final_app.mount("/", django_app)