# SIVIC — Sistema de Visión Inteligente para Condominios

Sistema de vigilancia inteligente con detección de infracciones por IA (YOLO), panel de cámaras en tiempo real estilo NVR (HikVision/Dahua), notificaciones WebSocket en tiempo real a guardias y gestión multicondominio.

---

## Estructura del proyecto

```
SmartCondominium/
└── apps/
    └── sivic_backend/      # API REST + WebSocket — Django 5 + DRF + Channels
        ├── core/           # Settings, URLs, ASGI
        ├── autenticacion/  # JWT propio, permisos Admin/Guardia
        ├── condominios/    # Condominios, suscripciones, planes
        ├── camaras/        # Registro, configuración y stream MJPEG de cámaras
        ├── reglas/         # Reglas de infracción para el modelo IA
        ├── eventos/        # Eventos detectados + integración YOLO
        ├── notificaciones/ # WebSocket tiempo real + historial persistente
        ├── auditoria/      # Log de acciones del sistema
        ├── datasets/       # Imágenes anotadas para entrenamiento
        └── db/
            ├── schema_sivic.sql      # Schema completo para Supabase
            └── schema_architect.xml  # Diagrama XMI para Enterprise Architect
```

---

## Tecnologías

| Capa | Stack |
|---|---|
| Backend | Django 5.2, DRF, Django Channels 4, PyJWT |
| Servidor ASGI | uvicorn (HTTP + WebSocket) |
| Base de datos | PostgreSQL vía Supabase |
| IA / Detección | YOLO (servidor externo) → `POST /api/eventos/inferencia/` |
| Notificaciones | WebSocket (tiempo real) vía Django Channels |
| Stream cámaras | MJPEG async (`StreamingHttpResponse` + async generator + OpenCV) |
| Email | Resend |

---

## Requisitos previos

- Python >= 3.11
- Cuenta Supabase (PostgreSQL)

---

## 1. Configuración inicial

```bash
cd apps/sivic_backend

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias clave (`requirements.txt`)

| Paquete | Para qué |
|---|---|
| `Django>=5.2` | Framework web, soporte async generator nativo |
| `channels>=4.0` | WebSocket con Django (protocolo ASGI) |
| `uvicorn>=0.30` | Servidor ASGI que corre HTTP y WebSocket |
| `djangorestframework>=3.16` | API REST |
| `PyJWT>=2.10` | Autenticación JWT (también valida tokens WS) |
| `opencv-python-headless>=4.9` | Captura y codificación MJPEG de cámaras |
| `ultralytics>=8.2` | Inferencia YOLO |
| `psycopg[binary]>=3.2` | Driver PostgreSQL |

---

## 2. Variables de entorno

Crear archivo `.env` en `apps/sivic_backend/` (no se commitea, está en `.gitignore`):

```env
SECRET_KEY=clave-secreta-larga-min-50-chars
DATABASE_URL=postgresql://usuario:password@host:5432/postgres
FIREBASE_CREDENTIALS_PATH=ruta/a/firebase-credentials.json
RESEND_API_KEY=re_xxxxxxxxxxxx
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.X
```

> `SECRET_KEY` se usa también para validar tokens JWT del WebSocket. Debe coincidir con el que firmó los tokens de login.

---

## 3. Base de datos

Copiar y ejecutar `apps/sivic_backend/db/schema_sivic.sql` en Supabase (Editor SQL).

---

## 4. Correr el servidor

**El servidor corre con `uvicorn`, NO con `python manage.py runserver`.**

`runserver` de Django no soporta WebSocket (usa WSGI). `uvicorn` corre el protocolo ASGI que permite HTTP y WebSocket simultáneamente.

```bash
cd apps/sivic_backend

python -m uvicorn core.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --timeout-graceful-shutdown 5
```

- `--host 0.0.0.0` — acepta conexiones desde la red local (necesario para Flutter en dispositivo físico y Angular en otra máquina)
- `--timeout-graceful-shutdown 5` — fuerza cierre en 5s al hacer Ctrl+C (sin esto el proceso se cuelga esperando que OpenCV libere capturas de cámara)

**Endpoints disponibles:**
- `http://localhost:8000/api/docs/` — Swagger UI interactivo
- `http://localhost:8000/api/redoc/` — ReDoc
- `ws://localhost:8000/ws/alertas/?token=<jwt>` — WebSocket de alertas en tiempo real

---

## 5. Notificaciones WebSocket

### Flujo completo

```
Servidor YOLO detecta infracción
        ↓
POST /api/eventos/inferencia/
        ↓
Django crea Evento en DB
        ↓
async_to_sync(channel_layer.group_send("sivic_alertas", {...}))
        ↓
AlertasConsumer.nueva_alerta() → websocket.send(JSON)
        ↓
Angular / Flutter reciben mensaje en tiempo real
```

### Protocolo WebSocket

**URL de conexión:**
```
ws://<host>:8000/ws/alertas/?token=<JWT>
```

El token JWT es el mismo que se obtiene del endpoint de login (`/api/autenticacion/login/`). Si el token es inválido o está ausente, el servidor cierra la conexión con código `4001`.

**Mensaje que recibe el cliente (JSON):**
```json
{
  "tipo": "alerta",
  "evento_id": 42,
  "camara_nombre": "Estacionamiento",
  "regla_nombre": "Merodeo",
  "confianza_ia": 0.91,
  "timestamp": "2026-06-13T18:45:00Z",
  "imagen_url": ""
}
```

### Implementación interna (Django Channels)

| Archivo | Rol |
|---|---|
| `notificaciones/consumers.py` | `AlertasConsumer` — valida JWT, une al grupo `sivic_alertas`, reenvía mensajes del grupo al WebSocket |
| `notificaciones/routing.py` | Mapea `/ws/alertas/` al consumer |
| `core/asgi.py` | `ProtocolTypeRouter` separa HTTP (Django) de WebSocket (Channels) |

Channel layer: `InMemoryChannelLayer` (en memoria, un solo proceso). Para multi-proceso usar `channels-redis`.

---

## 6. Stream MJPEG de cámaras

`GET /api/camaras/<id>/stream/` devuelve `StreamingHttpResponse` con `Content-Type: multipart/x-mixed-replace`.

Usa un **async generator** con OpenCV en hilo daemon:

- Hilo daemon abre `cv2.VideoCapture(rtsp_url)` con hasta 15 s de espera (RTSP en celular tarda 8-12 s)
- Generator async lee frames del hilo via `queue.Queue` con polling de 100 ms
- Ctrl+C cancela el task asyncio → `stop.set()` → hilo termina limpiamente (sin esta arquitectura el proceso se cuelga)
- Tiempo máximo sin frames antes de cortar: 20 s antes del primer frame, 3 s después

**Tipos de URL soportados:**

| Tipo | URL ejemplo |
|---|---|
| RTSP cámara IP | `rtsp://admin:pass@192.168.1.X:554/stream` |
| RTSP app celular (DailyRoutes / IP Webcam Pro) | `rtsp://192.168.1.X:5540/back` |
| HTTP MJPEG (IP Webcam Android) | `http://192.168.1.X:8080/video` |
| URL pública | `http://X.X.X.X/mjpg/video.mjpg` |

---

## 7. Integración IA (YOLO)

El servidor YOLO detecta una infracción y llama:

```http
POST /api/eventos/inferencia/
Content-Type: application/json

{
  "camara_id": 1,
  "regla_id": 2,
  "confianza": 0.91,
  "imagen_path": "capturas/evento_001.jpg"
}
```

El backend crea el evento y emite WebSocket a todos los guardias conectados.

**Reglas de detección (configurables en DB):**

| Regla | Umbral default | Descripción |
|---|---|---|
| Merodeo | 90 frames (3 min a 1 análisis/2 s) | Persona estática en zona restringida |
| Intrusión | configurable | Entrada a zona prohibida |
| Pelea | configurable | Altercado físico detectado |

---

## 8. Timestamps

Supabase almacena `TIMESTAMP WITHOUT TIME ZONE` en UTC. El serializer `EventoSerializer` trata toda fecha naive como UTC y siempre devuelve ISO 8601 con sufijo `Z`:

```
"timestamp_deteccion": "2026-06-13T18:45:00Z"
```

Angular muestra con `| date:'dd/MM/yy HH:mm':'-0400'` (Bolivia UTC-4).

---

## 9. Diagrama de base de datos

Abrir en **Enterprise Architect**:
`apps/sivic_backend/db/schema_architect.xml`

> File → Import Packages from XMI File → seleccionar el archivo → Import.
> El diagrama "ERD SIVIC" aparece en Database Package.

---

## Colaboradores

- Hebert Suárez Burgos
