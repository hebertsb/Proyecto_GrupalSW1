import os
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_PATH = os.getenv("PERRO_CORREA_MODEL_PATH", "modelo_correa_nuevo.pt")
BASE_MODEL_PATH = "yolov8n.pt"

class PerroCorreaDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        try:
            # Usamos YOLO puro + Heurística de proximidad de persona
            self.model_base = YOLO(BASE_MODEL_PATH)
            print("✅ PerroCorreaDetector (Proximity Heuristics) listo")
        except Exception as e:
            print(f"⚠️ Error al cargar PerroCorreaDetector base: {e}")
            self.model_base = None

    def detect(self, img, conf_min: float = 0.30) -> list:
        if self.model_base is None:
            return []
            
        results = self.model_base(img, verbose=False, conf=conf_min)
        
        perros_finales = []
        cajas_perros = []
        cajas_personas = []
        
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                clase_idx = int(box.cls[0])
                conf = float(box.conf[0])
                
                if clase_idx == 16: # Perro
                    cajas_perros.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                elif clase_idx == 0: # Persona
                    cajas_personas.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                    
        h, w = img.shape[:2]
                    
        for p in cajas_perros:
            x1, y1, x2, y2 = p["bbox"]
            px, py = (x1 + x2)/2, (y1 + y2)/2
            
            tiene_correa = False
            
            # Distancia a persona (si hay una persona muy cerca, asumimos que tiene correa)
            for per in cajas_personas:
                perx, pery = (per["bbox"][0] + per["bbox"][2])/2, (per["bbox"][1] + per["bbox"][3])/2
                dist = ((px - perx)**2 + (py - pery)**2)**0.5
                if dist < 250: # Dueño muy cerca
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
