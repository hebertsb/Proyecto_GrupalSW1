# SIVIC — Guía técnica: Detección IA y Cámaras (Backend)

> Autor: Hebert Suarez Burgos  
> Última actualización: 2026-06-21

---

## 1. Arquitectura general

```
Cámara IP / Celular
        │
        ▼
┌─────────────────────┐
│  Django (puerto 8001)│  ←── API REST + WebSocket
│  analizar_ia /       │
│  analizar_local      │
└────────┬────────────┘
         │  HTTP POST multipart (frame JPEG)
         ▼
┌──────────────────────────┐
│  Microservicio IA         │  Puerto 8002
│  entrenamientopersona/    │
│  api.py  →  POST /analizar│
└──────────────────────────┘
         │  JSON (detecciones + alertas)
         ▼
   Django registra Evento en BD
   Django envía WebSocket a clientes conectados
   Django sube frame a Supabase Storage como evidencia
```

---

## 2. Tipos de cámara

### Cámara IP / RTSP (cámara fija)
- Configurada en la BD con `rtsp_url` = URL RTSP real (ej. `rtsp://192.168.1.10:554/stream`)
- Django usa **OpenCV** para capturar un frame al recibir `POST /api/camaras/<id>/analizar_ia/`
- El stream se sirve al navegador como MJPEG via `GET /api/camaras/<id>/stream/`

### Cámara Local (celular con app Flutter)
- Configurada con `rtsp_url = local://<nombre>` (ej. `local://celular-1`)
- Flutter captura frames con la cámara trasera y los envía via `POST /api/camaras/<id>/analizar_local/`
- Django **no usa RTSP**: recibe el JPEG como multipart `file`
- El último frame recibido se guarda en `_ultimo_frame_cache[camara_id]` (dict en memoria)
- La web Angular puede ver ese frame via `GET /api/camaras/<id>/ultimo_frame/`

**Campo crítico en BD:** `rtsp_url`
- Si empieza con `local://` → cámara de celular
- Cualquier otra URL → cámara IP

---

## 3. Endpoints de cámaras

| Método | URL | Descripción |
|--------|-----|-------------|
| POST | `/api/camaras/<id>/analizar_ia/` | Captura frame por RTSP y lo analiza |
| POST | `/api/camaras/<id>/analizar_local/` | Recibe frame JPEG de Flutter y lo analiza |
| GET  | `/api/camaras/<id>/stream/` | Stream MJPEG para el navegador |
| GET  | `/api/camaras/<id>/ultimo_frame/` | Último frame recibido de cámara local |

---

## 4. Flujo de detección paso a paso

### `analizar_ia` (cámaras IP)
```
1. Django recibe POST /api/camaras/<id>/analizar_ia/
2. Verifica que la cámara sea alcanzable (ping HTTP al rtsp_url)
3. Captura un frame con OpenCV en un thread daemon (timeout 8s)
4. Redimensiona a 640px de ancho (para acelerar inferencia)
5. Codifica a JPEG calidad 70
6. Envía al microservicio IA: POST http://127.0.0.1:8002/api/analizar
   Body: { file: frame.jpg, camara_id, zonas_json, umbral_merodeo }
7. Recibe JSON con { alertas, detalle_alertas, detecciones, modo, raw }
8. Calcula conteo_personas y nivel (ver sección 6)
9. Para cada alerta → busca regla en BD → registrar_deteccion()
10. Sube frame a Supabase Storage como evidencia
11. Broadcast WebSocket a todos los clientes
12. Devuelve JSON de resultado al llamador (Flutter o Angular)
```

### `analizar_local` (cámaras de celular)
```
1. Flutter envía POST multipart con frame JPEG
2. Django decodifica con OpenCV, redimensiona a 640px
3. Guarda bytes en _ultimo_frame_cache[camara_id]
4. Mismo flujo desde paso 6 en adelante
```

---

## 5. El microservicio IA (`entrenamientopersona/api.py`)

Corre en `http://127.0.0.1:8002`. Para iniciarlo:
```bash
cd entrenamientopersona
uvicorn api:app --port 8002 --reload
```

### Modelos cargados al arrancar
| Modelo | Clase | Archivo | Detecta |
|--------|-------|---------|---------|
| YOLOv8n (COCO) | `PersonaDetector` | `yolov8n.pt` | Personas (clase 0) |
| YOLOv8n (COCO) | `VehiculoDetector` | `yolov8n.pt` | Autos, motos, camiones |
| ResNet / CNN custom | `PeleaClassifier` | `modelo_pelea.pth` | Peleas entre personas |

### Lógica de detección en `/api/analizar`
```
1. Detectar personas → PersonaDetector.detect(img, conf_min=0.35)
2. Detectar vehículos → VehiculoDetector.detect(img)
3. Determinar modo:
   - n_vehiculos > n_personas → modo "vehiculos"
   - caso contrario → modo "personas"
4. En modo "personas":
   - Verificar zonas restringidas (verificar_zonas)
   - Verificar merodeo (verificar_merodeo, acumula por camara_id)
   - Verificar pelea (PeleaClassifier, solo si ≥2 personas)
   - Verificar caída (verificar_caida, ratio bbox alto/ancho)
   - Verificar intrusión nocturna (hora del sistema)
   - Verificar acceso fuera de horario (zonas tipo horario_restringido)
5. En modo "vehiculos":
   - Verificar vehículos en zona restringida
6. Devolver JSON con alertas + detalle + detecciones + raw
```

---

## 6. Conteo de personas y niveles de alerta

Django calcula esto **después** de recibir la respuesta del microservicio:

```python
personas_det = [d for d in resultado['detecciones'] if d['clase'] in ('persona', 'person')]
conteo = len(personas_det)

nivel = 'critico'    if conteo >= 6 else
        'sospechoso' if conteo >= 3 else
        'normal'
```

| Conteo | Nivel | Color en UI |
|--------|-------|-------------|
| 0–2 personas | normal | Verde |
| 3–5 personas | sospechoso | Amarillo |
| 6+ personas | crítico | Rojo |

---

## 7. Mapa de alertas → reglas de BD

El `_MAPA_ALERTAS` conecta el nombre interno del microservicio IA con el `nombre_regla` en la tabla `reglas_infraccion`:

```python
_MAPA_ALERTAS = {
    'zona_restringida_persona':  'persona_zona_restringida',
    'merodeo':                   'merodeo',
    'vehiculo_zona_restringida': 'vehiculo_no_autorizado',
    'personas_peleando':         'personas_peleando',
    'caida_persona':             'caida_persona',
    'intrusion_nocturna':        'intrusion_nocturna',
    'acceso_fuera_horario':      'acceso_fuera_horario',
}
```

**Importante:** Si el admin no creó la regla con ese `nombre_regla` exacto en el panel web, el evento se ignora silenciosamente (`ReglaInfraccion.DoesNotExist` → `pass`).

---

## 8. Umbral de merodeo

El microservicio acumula cuántas veces detecta la misma persona cerca del mismo punto. El umbral controla cuántos análisis consecutivos deben ocurrir antes de disparar la alerta:

| Entorno | Valor | Tiempo real (análisis cada ~2s) |
|---------|-------|---------------------------------|
| Demo | 15 | ~30 segundos |
| Producción | 90 | ~3 minutos |

Se pasa como `umbral_merodeo` en el body del POST. Actualmente en 15 para demos.

---

## 9. Cómo agregar un nuevo modelo (ejemplo: detección de perros)

### Paso 1 — Crear el detector en el microservicio
```python
# entrenamientopersona/app/detectors/perro_detector.py
from ultralytics import YOLO

class PerroDetector:
    CLASE_IDS = [16]  # clase 16 = 'dog' en COCO

    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model = YOLO(model_path)

    def detect(self, img, conf_min: float = 0.40) -> list:
        results = self.model(img, verbose=False)
        perros = []
        for r in results:
            for box in r.boxes:
                if int(box.cls[0]) not in self.CLASE_IDS:
                    continue
                if float(box.conf[0]) < conf_min:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                perros.append({"bbox": [x1, y1, x2, y2], "confianza": round(float(box.conf[0]), 3)})
        return perros
```

### Paso 2 — Registrar en api.py
```python
from app.detectors.perro_detector import PerroDetector

perro_detector: Optional[PerroDetector] = None

@app.on_event("startup")
async def startup():
    global perro_detector
    perro_detector = PerroDetector()
```

### Paso 3 — Agregar regla en el endpoint /analizar
```python
# Dentro del if modo == "personas": (o crear propio)
if perro_detector:
    perros = perro_detector.detect(img)
    if perros:
        alertas_tipos.append("perro_detectado")
        alertas_detalle.append({"tipo": "perro_detectado", "confianza": perros[0]["confianza"]})
```

### Paso 4 — Agregar al mapa en Django (`camaras/views.py`)
```python
_MAPA_ALERTAS = {
    ...
    'perro_detectado': 'perro_en_area',  # nombre_regla exacto que el admin creó
}
```

### Paso 5 — El admin crea la regla en el panel web
- Ingresar al panel → Reglas → Nueva regla
- `nombre_regla` = `perro_en_area` (debe coincidir exactamente)

---

## 10. Variables de entorno críticas (`.env`)

No modificar sin entender las implicancias:

| Variable | Descripción |
|----------|-------------|
| `SIVIC_IA_URL` | URL del microservicio IA. Default `http://127.0.0.1:8002` |
| `DATABASE_URL` | PostgreSQL Supabase |
| `GROQ_API_KEY` | Clave API Groq para el asistente de reportes. **Nunca al repo** |
| `SUPABASE_URL` | URL de Supabase para subir evidencias |
| `SUPABASE_SERVICE_KEY` | Clave de servicio Supabase. **Nunca al repo** |
| `SECRET_KEY` | Clave secreta Django. **Nunca al repo** |

---

## 11. Archivos clave — no modificar sin saber qué hacen

| Archivo | Qué hace |
|---------|----------|
| `camaras/views.py` — `analizar_ia()` | Captura frame RTSP y llama al microservicio |
| `camaras/views.py` — `analizar_local()` | Recibe frame de Flutter y llama al microservicio |
| `camaras/views.py` — `_MAPA_ALERTAS` | Conecta alertas IA con reglas de BD |
| `camaras/views.py` — `_ultimo_frame_cache` | Dict en memoria con último JPEG por cámara local |
| `entrenamientopersona/app/detectors/persona_detector.py` | YOLOv8n — detecta personas |
| `entrenamientopersona/reglas/merodeo.py` | Acumula conteo de presencia por cámara |
| `eventos/services_ia.py` — `registrar_deteccion()` | Guarda evento en BD y notifica guardias |
| `core/settings.py` | Configuración Django. Leer `.env` aquí |
