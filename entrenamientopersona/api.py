import json
import os
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile

from app.detectors.persona_detector import PersonaDetector
from app.detectors.vehiculo_detector import VehiculoDetector
from app.classifiers.pelea_classifier import PeleaClassifier
from app.classifiers.vehiculo_estacionamiento_classifier import VehiculoEstacionamientoClassifier
from reglas.merodeo import limpiar_camara, verificar_merodeo
from reglas.zona_restringida import verificar_zonas
from reglas.caida import verificar_caida
from reglas.horario import verificar_intrusion_nocturna, verificar_acceso_fuera_horario

app = FastAPI(title="SIVIC — Detección Personas y Vehículos")
router = APIRouter()

# ── Configuración via variables de entorno ───────────────────────────────────
DJANGO_BACKEND_URL  = os.getenv("DJANGO_BACKEND_URL",  "http://127.0.0.1:8000")
DEFAULT_CAMARA_ID   = int(os.getenv("DEFAULT_CAMARA_ID",   "9"))
REGLA_PERSONA_ZONA  = int(os.getenv("REGLA_PERSONA_ZONA",  "3"))
REGLA_MERODEO       = int(os.getenv("REGLA_MERODEO",       "4"))
REGLA_VEHICULO_ZONA = int(os.getenv("REGLA_VEHICULO_ZONA", "6"))

# ── Detectores / clasificadores globales ─────────────────────────────────────
persona_detector:              Optional[PersonaDetector]                  = None
vehiculo_detector:             Optional[VehiculoDetector]                 = None
pelea_classifier:              Optional[PeleaClassifier]                  = None
vehiculo_estacionamiento_cls:  Optional[VehiculoEstacionamientoClassifier] = None


@app.on_event("startup")
async def startup():
    global persona_detector, vehiculo_detector, pelea_classifier, vehiculo_estacionamiento_cls
    persona_detector  = PersonaDetector()
    vehiculo_detector = VehiculoDetector()
    try:
        pelea_classifier = PeleaClassifier()
        print("[SIVIC] PeleaClassifier cargado")
    except FileNotFoundError as e:
        print(f"[SIVIC] PeleaClassifier no disponible: {e}")
    try:
        vehiculo_estacionamiento_cls = VehiculoEstacionamientoClassifier()
        print("[SIVIC] VehiculoEstacionamientoClassifier cargado")
    except FileNotFoundError as e:
        print(f"[SIVIC] VehiculoEstacionamientoClassifier no disponible: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _leer_imagen(contents: bytes):
    img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Imagen inválida")
    return img



def _normalizar(bboxes: list, alto: int, ancho: int, clase: str, extra_fn=None) -> list:
    out = []
    for b in bboxes:
        x1, y1, x2, y2 = b["bbox"]
        entry = {
            "clase": clase,
            "confianza": b["confianza"],
            "bbox": {
                "x": x1 / ancho, "y": y1 / alto,
                "w": (x2 - x1) / ancho, "h": (y2 - y1) / alto,
            },
        }
        if extra_fn:
            entry.update(extra_fn(b))
        out.append(entry)
    return out


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.get("/health")
async def health():
    return {
        "status": "ok",
        "persona_detector":  persona_detector  is not None,
        "vehiculo_detector": vehiculo_detector is not None,
        "pelea_classifier":  pelea_classifier  is not None,
    }


@router.post("/detect/personas")
async def detect_personas(file: UploadFile = File(...)):
    if not persona_detector:
        raise HTTPException(500, "Detector no inicializado")
    img = _leer_imagen(await file.read())
    personas = persona_detector.detect(img)
    return {"personas_detectadas": len(personas), "bounding_boxes": [p["bbox"] for p in personas]}


@router.post("/detect/vehiculos")
async def detect_vehiculos(file: UploadFile = File(...)):
    if not vehiculo_detector:
        raise HTTPException(500, "Detector no inicializado")
    img = _leer_imagen(await file.read())
    vehiculos = vehiculo_detector.detect(img)
    return {"vehiculos_detectados": len(vehiculos), "detecciones": vehiculos}


@router.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    camara_id:      int           = Form(DEFAULT_CAMARA_ID),
    zonas_json:     Optional[str] = Form(None),   # JSON de zonas prohibidas
    umbral_merodeo: int           = Form(30),      # segundos para merodeo
):
    """
    Endpoint principal. Recibe frame de cámara y devuelve detecciones + alertas.

    zonas_json (opcional):
    [{"nombre":"Entrada","puntos":[[10,20],[200,20],[200,300],[10,300]],"normalizado":false}]
    Si normalizado=true, coordenadas van de 0.0 a 1.0 relativas a la imagen.
    """
    if not persona_detector or not vehiculo_detector:
        raise HTTPException(500, "Detectores no inicializados")

    img = _leer_imagen(await file.read())
    alto, ancho = img.shape[:2]
    zonas = json.loads(zonas_json) if zonas_json else []

    # ── Detectar ambas clases siempre (independiente) ────────────────────────
    personas  = persona_detector.detect(img)
    vehiculos = vehiculo_detector.detect(img)

    alertas_tipos   = []
    alertas_detalle = []

    # ── Alertas de PERSONAS ───────────────────────────────────────────────────

    # 1. Personas en zona restringida
    if zonas and personas:
        for v in verificar_zonas(personas, zonas, alto, ancho):
            alertas_tipos.append("zona_restringida_persona")
            alertas_detalle.append({"tipo": "zona_restringida_persona", **v})

    # 2. Merodeo
    if personas:
        for m in verificar_merodeo(personas, camara_id, umbral_merodeo):
            alertas_tipos.append("merodeo")
            alertas_detalle.append({"tipo": "merodeo", **m})

    # 3. Pelea (mínimo 2 personas)
    if pelea_classifier and len(personas) >= 2:
        resultado_pelea = pelea_classifier.clasificar(img)
        if resultado_pelea["pelea"]:
            alertas_tipos.append("personas_peleando")
            alertas_detalle.append({
                "tipo":      "personas_peleando",
                "confianza": resultado_pelea["confianza"],
            })

    # 4. Caída de persona
    for c in verificar_caida(personas):
        alertas_tipos.append("caida_persona")
        alertas_detalle.append({"tipo": "caida_persona", **c})

    # 5. Intrusión nocturna
    for n in verificar_intrusion_nocturna(personas):
        alertas_tipos.append("intrusion_nocturna")
        alertas_detalle.append({"tipo": "intrusion_nocturna", **n})

    # 6. Acceso fuera de horario
    for h in verificar_acceso_fuera_horario(personas, zonas, alto, ancho):
        alertas_tipos.append("acceso_fuera_horario")
        alertas_detalle.append({"tipo": "acceso_fuera_horario", **h})

    # ── Alertas de VEHÍCULOS ──────────────────────────────────────────────────

    # 7. Vehículo en zona restringida
    if zonas and vehiculos:
        for v in verificar_zonas(vehiculos, zonas, alto, ancho):
            alertas_tipos.append("vehiculo_zona_restringida")
            alertas_detalle.append({"tipo": "vehiculo_zona_restringida", **v})

    # 8. Vehículo mal estacionado (requiere modelo entrenado)
    if vehiculo_estacionamiento_cls and vehiculos:
        resultado_est = vehiculo_estacionamiento_cls.clasificar(img)
        if resultado_est["infraccion"]:
            alertas_tipos.append("vehiculo_mal_estacionado")
            alertas_detalle.append({
                "tipo":      "vehiculo_mal_estacionado",
                "confianza": resultado_est["confianza"],
                "clase":     resultado_est["clase"],
            })

    # ── Respuesta ─────────────────────────────────────────────────────────────
    return {
        "alertas":         alertas_tipos,
        "detalle_alertas": alertas_detalle,
        "detecciones":     _normalizar(personas, alto, ancho, "persona") +
                           _normalizar(vehiculos, alto, ancho, "vehiculo",
                                       extra_fn=lambda b: {"tipo_vehiculo": b.get("tipo", "auto")}),
        "conteo": {
            "personas":  len(personas),
            "vehiculos": len(vehiculos),
        },
        "raw": {"personas": personas, "vehiculos": vehiculos},
    }


@router.delete("/historial/limpiar/{camara_id}")
async def limpiar_historial(camara_id: int):
    limpiar_camara(camara_id)
    return {"ok": True, "camara_id": camara_id}


# Registrar con y sin prefijo /api (igual que Luis)
app.include_router(router, prefix="/api")
app.include_router(router, prefix="")
