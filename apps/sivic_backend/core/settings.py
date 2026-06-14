"""
SIVIC Backend — Sistema de Visión con IA para Condominios
"""
from pathlib import Path
import os
import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".onrender.com"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # Módulos SIVIC
    "autenticacion",
    "condominios",
    "camaras",
    "reglas",
    "eventos",
    "auditoria",
    "datasets",
    "notificaciones",
    "pagos",
    "drf_spectacular",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Base de datos — apunta a Supabase PostgreSQL (schema en db/schema_sivic.sql)
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
    )
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "autenticacion.autenticacion_jwt.AutenticacionJWT",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SIVIC API",
    "DESCRIPTION": "Sistema de Visión con IA para Condominios — API REST",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "Autenticación",  "description": "Login, registro, gestión de usuarios"},
        {"name": "Condominios",    "description": "Condominios, planes SaaS y suscripciones"},
        {"name": "Cámaras",       "description": "Cámaras IP y zonas ROI"},
        {"name": "Reglas",        "description": "Reglas de infracción"},
        {"name": "Eventos",       "description": "Detecciones IA y gestión de alertas"},
        {"name": "Notificaciones", "description": "Historial de notificaciones push"},
        {"name": "Auditoría",     "description": "Logs de auditoría (solo admin)"},
        {"name": "Datasets",      "description": "Datasets para re-entrenamiento IA"},
    ],
}

LANGUAGE_CODE = "es-bo"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

# Stripe — claves disponibles en dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY      = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET  = env("STRIPE_WEBHOOK_SECRET", default="")

# Ruta al modelo YOLO entrenado (.pt). Dejar vacío si no se usa IA local.
# Ejemplo: YOLO_MODEL_PATH=apps/sivic_backend/modelos/sivic.pt
YOLO_MODEL_PATH = env("YOLO_MODEL_PATH", default="")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_ALL_ORIGINS = DEBUG
