# SIVIC — Sistema de Visión Inteligente para Condominios

Sistema de vigilancia inteligente con detección de infracciones por IA (YOLO), panel de cámaras en tiempo real estilo NVR (HikVision/Dahua), notificaciones push a guardias y gestión multicondominio.

---

## Estructura del proyecto

```
SmartCondominium/
└── apps/
    ├── sivic_backend/      # API REST — Django 5 + DRF
    │   ├── core/           # Settings, URLs, WSGI
    │   ├── autenticacion/  # JWT propio, permisos Admin/Guardia
    │   ├── condominios/    # Condominios, suscripciones, planes
    │   ├── camaras/        # Registro y configuración de cámaras
    │   ├── reglas/         # Reglas de infracción para el modelo IA
    │   ├── eventos/        # Eventos detectados + integración YOLO
    │   ├── notificaciones/ # Push FCM + historial persistente
    │   ├── auditoria/      # Log de acciones del sistema
    │   ├── datasets/       # Imágenes anotadas para entrenamiento
    │   └── db/
    │       ├── schema_sivic.sql      # Schema completo para Supabase
    │       └── schema_architect.xml  # Diagrama XMI para Enterprise Architect
    │
    ├── sivic_web/          # Panel de administración — Angular 17
    │   └── src/app/
    │       ├── autenticacion/   # Login
    │       ├── panel-camaras/   # Panel NVR: cuadrícula 1×1/2×2/3×3/4×4
    │       ├── eventos/         # Lista y gestión de eventos
    │       ├── configuracion/   # Cámaras, reglas, usuarios
    │       ├── auditoria/       # Logs del sistema
    │       └── compartido/      # Modelos, servicios, componentes reutilizables
    │
    └── sivic_mobile/       # App de guardia — Flutter
        └── lib/
            ├── main.dart
            ├── nucleo/          # Temas, HTTP, rutas, proveedores Riverpod
            ├── pantallas/       # Login, Cámaras (grid), Eventos
            └── compartido/      # Modelos, widgets
```

---

## Tecnologías

| Capa | Stack |
|---|---|
| Backend | Django 5.2, DRF, PyJWT, drf-spectacular, psycopg3 |
| Base de datos | PostgreSQL vía Supabase |
| IA / Detección | YOLO (servidor externo) → `POST /api/eventos/inferencia/` |
| Notificaciones | Firebase Cloud Messaging (FCM) |
| Email | Resend |
| Web | Angular 17 (standalone), SCSS con variables CSS |
| Mobile | Flutter 3, Riverpod, GoRouter, Dio, VideoPlayer |
| Stream cámaras | MJPEG (`<img>` src), HLS (mediamtx proxy), archivo de video |

---

## Requisitos previos

- Python ≥ 3.11
- Node.js ≥ 18 + Angular CLI 17 (`npm i -g @angular/cli`)
- Flutter ≥ 3.19
- Cuenta Supabase (PostgreSQL)
- Proyecto Firebase (para FCM)

---

## 1. Backend — `apps/sivic_backend/`

### Configuración inicial

```bash
cd apps/sivic_backend

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### Variables de entorno

Crear archivo `.env` en `apps/sivic_backend/` basado en `.env.example`:

```env
SECRET_KEY=clave-secreta-larga
DATABASE_URL=postgresql://usuario:password@host:5432/postgres
FIREBASE_CREDENTIALS_PATH=ruta/a/firebase-credentials.json
RESEND_API_KEY=re_xxxxxxxxxxxx
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Base de datos

Copiar y ejecutar `apps/sivic_backend/db/schema_sivic.sql` en Supabase (Editor SQL).

### Correr el servidor

```bash
python manage.py runserver
```

**Endpoints disponibles:**
- `http://localhost:8000/api/docs/` — Swagger UI interactivo
- `http://localhost:8000/api/redoc/` — ReDoc

---

## 2. Frontend Web — `apps/sivic_web/`

```bash
cd apps/sivic_web
npm install
ng serve
```

Acceder a `http://localhost:4200`

La URL del backend se configura en `src/environments/environment.ts`:
```typescript
export const entorno = {
  produccion: false,
  apiUrl: 'http://localhost:8000/api',
};
```

### Pantallas disponibles

| Ruta | Rol | Descripción |
|---|---|---|
| `/login` | Todos | Autenticación |
| `/camaras` | Todos | Panel NVR de cámaras en tiempo real |
| `/eventos` | Todos | Listado y gestión de eventos IA |
| `/configuracion/camaras` | Admin | Alta/baja de cámaras y URLs de stream |
| `/configuracion/reglas` | Admin | Reglas de detección y umbrales |
| `/configuracion/usuarios` | Admin | Usuarios del sistema |
| `/auditoria` | Admin | Log de acciones |

### Modos de stream soportados

| Tipo | Cómo configurar |
|---|---|
| `mjpeg` | App **IP Webcam** (Android) → `http://IP:8080/video` |
| `hls` | Proxy **mediamtx** → `http://IP:8888/nombre/index.m3u8` |
| `archivo` | Ruta local o URL de video `.mp4` |

---

## 3. App móvil — `apps/sivic_mobile/`

```bash
cd apps/sivic_mobile
flutter pub get
flutter run
```

Para emulador Android, el backend corre en `10.0.2.2:8000` (alias de localhost).  
Para dispositivo físico, cambiar `_urlBase` en `lib/nucleo/red/cliente_http.dart` por la IP local del PC.

### Funcionalidades

- Panel de cámaras en tiempo real (MJPEG / HLS / archivo)
- Lista de eventos con filtros por estado
- Cambio de estado inline (Pendiente → En revisión → Resuelto)
- Tema oscuro/claro
- Sesión persistente con JWT

---

## 4. Integración IA (YOLO)

El servidor YOLO detecta una infracción y llama:

```http
POST /api/eventos/inferencia/
Content-Type: application/json

{
  "camara_id": 1,
  "regla_id": 2,
  "confianza": 0.91,
  "imagen_path": "capturas/evento_001.jpg",
  "guardias": [
    { "usuario_id": 3, "token_fcm": "TOKEN_FCM_DEL_GUARDIA" }
  ]
}
```

El backend crea el evento, envía push a los guardias vía FCM y persiste el registro en la tabla `notificaciones`.

---

## 5. Diagrama de base de datos

Abrir en **Enterprise Architect**:
`apps/sivic_backend/db/schema_architect.xml`

> File → Import Packages from XMI File → seleccionar el archivo → Import.  
> El diagrama "ERD SIVIC" aparece en Database Package.

---

## Flujo general del sistema

```
Cámara IP / IP Webcam
        ↓
  servidor YOLO
        ↓
POST /api/eventos/inferencia/
        ↓
Django crea Evento + envía FCM
        ↓
Guardia recibe notificación push
        ↓
App Flutter / Web → gestiona el evento
```

---

## Colaboradores

- Hebert Suárez Burgos
