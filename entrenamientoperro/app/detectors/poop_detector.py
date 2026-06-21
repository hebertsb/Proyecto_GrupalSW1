import random
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

class PoopDetector:
    def __init__(self, model_path: str = r"D:\SW1\entrenamientoperro\models\feces_yolo.pt"):
        self.model_path = Path(model_path)
        self.model = None
        
        if self.model_path.exists():
            try:
                self.model = YOLO(str(self.model_path))
                print(f"✅ PoopDetector cargado con éxito desde {self.model_path}")
            except Exception as e:
                print(f"⚠️ Error al cargar el modelo de heces: {e}")
        else:
            print(f"⚠️ Advertencia: No se encontró el modelo de heces en {self.model_path}. Se usará simulación.")

    def detect(self, image_cv2) -> list:
        if self.model is not None:
            try:
                results = self.model(image_cv2, verbose=False)
                heces = []
                for r in results:
                    for box in r.boxes:
                        conf = float(box.conf[0])
                        if conf >= 0.60: # Incrementar umbral para evitar falsos positivos con hojas secas
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            clase_id = int(box.cls[0])
                            heces.append({
                                "bbox": [x1, y1, x2, y2],
                                "confianza": conf,
                                "clase": "heces"
                            })
                return heces
            except Exception as e:
                print(f"Error en detección real de heces: {e}")
                
        # Fallback a simulación
        if random.random() < 0.20:
            alto, ancho = image_cv2.shape[:2]
            conf = round(random.uniform(0.5, 0.95), 2)
            x1 = int(ancho * 0.4)
            y1 = int(alto * 0.6)
            x2 = int(ancho * 0.6)
            y2 = int(alto * 0.9)
            return [{
                "bbox": [x1, y1, x2, y2],
                "confianza": conf,
                "clase": "Simulado"
            }]
        
        return []
