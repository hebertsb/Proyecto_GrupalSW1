import os
import cv2
from ultralytics import YOLO

MODEL_PATH = os.getenv("PERRO_CORREA_MODEL_PATH", "modelo_correa_nuevo.pt")
BASE_MODEL_PATH = "yolov8n.pt"

class PerroCorreaDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        try:
            # Cargamos TU modelo personalizado para detectar los perros
            self.model_custom = YOLO(model_path)
            # Cargamos YOLO base solo para detectar a las personas (dueños)
            self.model_base = YOLO(BASE_MODEL_PATH)
            print("✅ PerroCorreaDetector (Modelo Custom + Heurística) listo")
        except Exception as e:
            print(f"⚠️ Error al cargar PerroCorreaDetector: {e}")
            self.model_custom = None
            self.model_base = None

    def detect(self, img, conf_min: float = 0.30) -> list:
        if self.model_custom is None or self.model_base is None:
            return []
            
        # 1. Detectar perros con TU modelo
        results_custom = self.model_custom(img, verbose=False, conf=conf_min)
        
        # 2. Detectar personas con YOLO base — siempre 0.30 para no perder dueños
        results_base = self.model_base(img, verbose=False, conf=0.30)
        
        perros_finales = []
        cajas_perros = []
        cajas_personas = []
        
        # Extraer perros de tu modelo
        for r in results_custom:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                clase = r.names[int(box.cls[0])].lower()
                # Si el modelo ya detectó "leash"/"correa" en el nombre → perro con correa
                # "dog-without-leash" contains "leash" → must exclude "without"
                tiene_correa_modelo = ("leash" in clase or "correa" in clase) and "without" not in clase and "sin" not in clase
                cajas_perros.append({
                    "bbox": [x1, y1, x2, y2],
                    "confianza": conf,
                    "clase": clase,
                    "tiene_correa_modelo": tiene_correa_modelo,
                })

        # Extraer personas del modelo base
        for r in results_base:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                clase_idx = int(box.cls[0])
                conf_per = float(box.conf[0])
                if clase_idx == 0:  # Persona
                    cajas_personas.append({"bbox": [x1, y1, x2, y2], "confianza": conf_per})

        # Aplicar heurística de proximidad solo cuando el modelo no fue explícito
        for p in cajas_perros:
            tiene_correa = p.get("tiene_correa_modelo", False)
            clase_perro  = p.get("clase", "")

            # Modelo explicitó "sin correa" → confiar directamente, no aplicar proximidad
            suelto_explicito = "without" in clase_perro or "sin" in clase_perro

            if not tiene_correa and not suelto_explicito:
                # Clase ambigua (ej: dangerous_dogs) → usar heurística de proximidad
                x1, y1, x2, y2 = p["bbox"]
                px, py = (x1 + x2) / 2, (y1 + y2) / 2
                for per in cajas_personas:
                    perx = (per["bbox"][0] + per["bbox"][2]) / 2
                    pery = (per["bbox"][1] + per["bbox"][3]) / 2
                    dist = ((px - perx) ** 2 + (py - pery) ** 2) ** 0.5
                    if dist < 400:
                        tiene_correa = True
                        print("[Logica] Dueño cerca del perro, asumiendo correa.")
                        break

            es_suelto = not tiene_correa
            
            perros_finales.append({
                "bbox": p["bbox"],
                "confianza": round(p["confianza"], 3),
                "suelto": es_suelto
            })
            
        return perros_finales
