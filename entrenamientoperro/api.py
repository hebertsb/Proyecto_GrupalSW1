from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter
from fastapi.responses import FileResponse
import cv2
import numpy as np
import random
from pathlib import Path
from ultralytics import YOLO
from app.classifier.resnet_classifier import ResNetClassifier
from app.detectors.poop_detector import PoopDetector

app = FastAPI(title="FastAPI en Django")
router = APIRouter()

import os

model = None
resnet_classifier = None
clasificador_real = False
poop_detector = None
LAST_DETECTED_BREED = None
IMAGES_DIR = Path(os.getenv("DOGS_IMAGES_DIR", "data/raw/stanford_dogs/Images"))



@app.on_event("startup")
async def startup_event():
    global model, resnet_classifier, clasificador_real, poop_detector
    # Cargar el modelo YOLO para perros
    model = YOLO("yolov8n.pt")
    
    # Cargar el clasificador ResNet50
    model_path   = Path(os.getenv("DOGS_RESNET_PATH",   "models/resnet50_dogs.pth"))
    classes_path = Path(os.getenv("DOGS_CLASSES_PATH",  "models/classes.json"))
    
    if model_path.exists() and classes_path.exists():
        try:
            resnet_classifier = ResNetClassifier(
                model_path=str(model_path),
                classes_path=str(classes_path)
            )
            clasificador_real = True
            print("✅ ResNetClassifier cargado con éxito para clasificación de razas.")
        except Exception as e:
            print(f"⚠️ Error al cargar ResNetClassifier: {e}")
            resnet_classifier = None
            clasificador_real = False
    else:
        print("⚠️ Advertencia: No se encontró resnet50_dogs.pth o classes.json. Se usará clasificación simulada.")
        resnet_classifier = None
        clasificador_real = False
        
    # Cargar el detector de heces
    poop_detector = PoopDetector()

@router.get("/fastapi-endpoint")
async def root():
    return {"message": "¡Hola desde FastAPI funcionando en Django!"}

@router.get("/health")
async def health():
    poop_loaded = poop_detector is not None and poop_detector.model is not None
    return {
        "status": "ok", 
        "yolo_loaded": model is not None, 
        "resnet_loaded": clasificador_real,
        "poop_loaded": poop_loaded
    }

@router.post("/detect/dogs")
async def detect_dogs(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=500, detail="YOLO model is not loaded yet")
    
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    # Realizar detección
    results = model(img)
    perros = []
    
    for r in results:
        for box in r.boxes:
            clase_id = int(box.cls[0])
            if clase_id == 16:  # Clase 'dog' en COCO
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                perros.append([x1, y1, x2, y2])
                
    return {
        "perros_detectados": len(perros),
        "bounding_boxes": perros
    }

@router.get("/razas")
async def get_razas():
    if not IMAGES_DIR.exists():
        return []
    return sorted([d.name for d in IMAGES_DIR.iterdir() if d.is_dir()])

@router.get("/razas/{raza_id}/imagen")
async def get_raza_imagen(raza_id: str):
    breed_dir = IMAGES_DIR / raza_id
    if not breed_dir.exists() or not breed_dir.is_dir():
        raise HTTPException(status_code=404, detail="Raza no encontrada")
    images = list(breed_dir.glob("*.jpg"))
    if not images:
        raise HTTPException(status_code=404, detail="No se encontraron imágenes para esta raza")
    random_image = random.choice(images)
    return FileResponse(random_image)

@router.get("/dataset/stats")
async def get_dataset_stats():
    if not IMAGES_DIR.exists():
        return {"total_razas": 0, "total_imagenes": 0}
    razas = [d for d in IMAGES_DIR.iterdir() if d.is_dir()]
    total_imgs = sum(1 for _ in IMAGES_DIR.rglob("*.jpg"))
    return {
        "total_razas": len(razas),
        "total_imagenes": total_imgs
    }

@router.post("/detect/poop")
async def detect_poop(file: UploadFile = File(...)):
    if poop_detector is None:
        raise HTTPException(status_code=500, detail="Poop detector is not loaded yet")
    
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    heces = poop_detector.detect(img)
    if heces:
        best = max(heces, key=lambda x: x["confianza"])
        return {
            "hay_heces": True,
            "bbox": best["bbox"],
            "confianza": best["confianza"],
            "clase": best.get("clase", "Feces")
        }
    else:
        return {"hay_heces": False}

@router.post("/analizar")
async def analizar(imagen: UploadFile = File(None), file: UploadFile = File(None)):
    if model is None or poop_detector is None:
        raise HTTPException(status_code=500, detail="Models are not loaded yet")
    
    upload_file = imagen or file
    if not upload_file:
        raise HTTPException(status_code=400, detail="No image file provided. Use field 'imagen' or 'file'")
        
    contents = await upload_file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    alto, ancho = img.shape[:2]
    
    # 1. Detectar perros y personas con YOLO
    results = model(img)
    bboxes_perros = []
    bboxes_personas = []
    
    for r in results:
        for box in r.boxes:
            clase_id = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            if conf >= 0.25:
                if clase_id == 16:  # dog
                    bboxes_perros.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                elif clase_id == 0:  # person
                    bboxes_personas.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                
    alertas = []
    
    # Evaluar si el perro está sin correa (suelto) usando proximidad espacial
    for perro in bboxes_perros:
        px1, py1, px2, py2 = perro["bbox"]
        px_c = (px1 + px2) / 2
        py_c = (py1 + py2) / 2
        
        distancia_minima = float('inf')
        for persona in bboxes_personas:
            hx1, hy1, hx2, hy2 = persona["bbox"]
            hx_c = (hx1 + hx2) / 2
            hy_c = (hy1 + hy2) / 2
            
            dist = np.sqrt((px_c - hx_c)**2 + (py_c - hy_c)**2)
            if dist < distancia_minima:
                distancia_minima = dist
        
        # Umbral: 25% del ancho de la imagen. Si está más lejos, o no hay humanos, está suelto.
        umbral_distancia = ancho * 0.25
        if distancia_minima > umbral_distancia:
            if "sin_correa" not in alertas:
                alertas.append("sin_correa")
            
    # 2. Detectar heces (real o simulado)
    heces_detectadas = poop_detector.detect(img)
    if heces_detectadas:
        alertas.append("heces_no_limpiadas")
        
    raza = None
    
    # El estado general es simulado si alguno de los clasificadores/detectores reales está ausente
    poop_real = poop_detector.model is not None
    simulado = not (clasificador_real and poop_real)
    
    global LAST_DETECTED_BREED
    
    if not bboxes_perros:
        # Si no hay perros en escena, limpiamos la cache
        LAST_DETECTED_BREED = None

    if clasificador_real and resnet_classifier:
        raza_detectada = None
        
        # Si ya clasificamos este perro, usamos la caché el 90% de las veces para ahorrar 200ms de CPU por frame
        if bboxes_perros and LAST_DETECTED_BREED and random.random() > 0.1:
            raza_detectada = LAST_DETECTED_BREED
        elif bboxes_perros:
            x1, y1, x2, y2 = bboxes_perros[0]["bbox"]
            crop = img[max(0, y1):min(alto, y2), max(0, x1):min(ancho, x2)]
            if crop.size > 0:
                try:
                    raza_detectada = resnet_classifier.predict(crop)
                    if raza_detectada:
                        LAST_DETECTED_BREED = raza_detectada
                except Exception as e:
                    print(f"Error prediciendo crop: {e}")
        
        if not raza_detectada and bboxes_perros:
            if LAST_DETECTED_BREED:
                raza_detectada = LAST_DETECTED_BREED
            else:
                try:
                    raza_detectada = resnet_classifier.predict(img)
                    if raza_detectada:
                        LAST_DETECTED_BREED = raza_detectada
                except Exception as e:
                    raza_detectada = "Chihuahua"
                    
        raza = raza_detectada
        if raza:
            raza = raza.title()
    else:
        razas_predefinidas = ["Chihuahua", "Golden Retriever", "Pug", "German Shepherd", "Beagle"]
        raza = random.choice(razas_predefinidas) + " (Simulado)"
            
    # 3. Enviar notificaciones/webhooks a Django
    import requests
    DJANGO_BACKEND_URL = os.getenv("DJANGO_BACKEND_URL", "http://127.0.0.1:8001")
    DEFAULT_CAMARA_ID = int(os.getenv("DEFAULT_CAMARA_ID", 9))
    
    if "sin_correa" in alertas:
        try:
            conf = bboxes_perros[0]["confianza"] if bboxes_perros else 0.85
            payload = {
                "camara_id": DEFAULT_CAMARA_ID,
                "regla_id": 2,  # mascota_suelta
                "confianza": conf,
                "imagen_path": "frames/evidencia_sin_correa.jpg"
            }
            resp = requests.post(f"{DJANGO_BACKEND_URL}/api/eventos/inferencia/", json=payload, timeout=3)
            if resp.status_code == 201:
                print("Webhook 'mascota_suelta' enviado con exito a Django.")
            else:
                print(f"Error al enviar Webhook 'mascota_suelta': Status {resp.status_code}, Body: {resp.text}")
        except Exception as e:
            print(f"Advertencia: No se pudo enviar webhook 'mascota_suelta' a Django: {e}")
            
    if "heces_no_limpiadas" in alertas:
        try:
            conf = heces_detectadas[0]["confianza"] if heces_detectadas else 0.85
            payload = {
                "camara_id": DEFAULT_CAMARA_ID,
                "regla_id": 5,  # heces_no_limpiadas
                "confianza": conf,
                "imagen_path": "frames/evidencia_heces.jpg"
            }
            resp = requests.post(f"{DJANGO_BACKEND_URL}/api/eventos/inferencia/", json=payload, timeout=3)
            if resp.status_code == 201:
                print("Webhook 'heces_no_limpiadas' enviado con exito a Django.")
            else:
                print(f"Error al enviar Webhook 'heces_no_limpiadas': Status {resp.status_code}, Body: {resp.text}")
        except Exception as e:
            print(f"Advertencia: No se pudo enviar webhook 'heces_no_limpiadas' a Django: {e}")

    # Estandarizar detecciones para compatibilidad del frontend (coordenadas normalizadas 0-1)
    detecciones_compatibles = []
    for p in bboxes_perros:
        px1, py1, px2, py2 = p["bbox"]
        detecciones_compatibles.append({
            "clase": "dog",
            "confianza": round(p["confianza"], 3),
            "bbox": {
                "x": px1 / ancho,
                "y": py1 / alto,
                "w": (px2 - px1) / ancho,
                "h": (py2 - py1) / alto
            }
        })
    for p in bboxes_personas:
        px1, py1, px2, py2 = p["bbox"]
        detecciones_compatibles.append({
            "clase": "person",
            "confianza": round(p["confianza"], 3),
            "bbox": {
                "x": px1 / ancho,
                "y": py1 / alto,
                "w": (px2 - px1) / ancho,
                "h": (py2 - py1) / alto
            }
        })
    for h in heces_detectadas:
        hx1, hy1, hx2, hy2 = h["bbox"]
        detecciones_compatibles.append({
            "clase": "feces",
            "confianza": round(h["confianza"], 3),
            "bbox": {
                "x": hx1 / ancho,
                "y": hy1 / alto,
                "w": (hx2 - hx1) / ancho,
                "h": (hy2 - hy1) / alto
            }
        })

    return {
        "alertas": alertas,
        "raza": raza,
        "simulado": simulado,
        "detecciones": detecciones_compatibles,
        "raw_detecciones": {
            "perros": bboxes_perros,
            "personas": bboxes_personas,
            "heces": heces_detectadas
        }
    }

@router.post("/clasificar/raza")
@router.get("/clasificar/raza")
async def clasificar_raza(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    if clasificador_real and resnet_classifier:
        try:
            raza = resnet_classifier.predict(img)
            return {"raza": raza, "clasificacion_real": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Inference error: {e}")
    else:
        razas_predefinidas = ["Chihuahua", "Golden Retriever", "Pug", "German Shepherd", "Beagle"]
        raza = random.choice(razas_predefinidas) + " (Simulado - No entrenado)"
        return {"raza": raza, "clasificacion_real": False}

# Registrar rutas para que funcionen con o sin el prefijo /api
app.include_router(router, prefix="/api")
app.include_router(router, prefix="")