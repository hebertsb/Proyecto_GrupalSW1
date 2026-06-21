import os
from ultralytics import YOLO

MODEL_PATH = os.getenv("PERRO_CORREA_MODEL_PATH", "modelo_correa_nuevo.pt")

class PerroCorreaDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        try:
            self.model = YOLO(model_path)
            print("✅ PerroCorreaDetector (Nuevo) listo")
        except Exception as e:
            print(f"⚠️ Error al cargar PerroCorreaDetector: {e}")
            self.model = None

    def detect(self, img, conf_min: float = 0.40) -> list:
        if self.model is None:
            return []
        
        # Hacemos la inferencia con NMS agnóstico (evita doble caja para el mismo perro)
        results = self.model(img, verbose=False, agnostic_nms=True, iou=0.45)
        perros_correa = []
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < conf_min:
                    continue
                    
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                clase_idx = int(box.cls[0])
                nombre_clase = self.model.names[clase_idx]
                
                print(f"[YOLO Correa] Detectó: {nombre_clase} ({conf:.2f})")
                
                # Clase 1: Perro SIN correa (Alerta)
                if nombre_clase == "Dog-without-Leash":
                    perros_correa.append({
                        "bbox": [x1, y1, x2, y2],
                        "confianza": round(conf, 3),
                        "suelto": True
                    })
                # Clase 2: Perro CON correa (Sin alerta)
                elif nombre_clase == "dog leash":
                    perros_correa.append({
                        "bbox": [x1, y1, x2, y2],
                        "confianza": round(conf, 3),
                        "suelto": False
                    })
                    
        return perros_correa
