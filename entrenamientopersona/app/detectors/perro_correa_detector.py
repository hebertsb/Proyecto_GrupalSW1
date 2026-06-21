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
        
        # SIN agnostic_nms para permitir que ambas clases (suelto y con correa) se detecten simultáneamente si el modelo duda.
        results = self.model(img, verbose=False, iou=0.45)
        
        cajas_sueltos = []
        cajas_correa = []
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < conf_min:
                    continue
                    
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                clase_idx = int(box.cls[0])
                nombre_clase = self.model.names[clase_idx]
                
                print(f"[YOLO Correa] Detectó: {nombre_clase} ({conf:.2f})")
                
                if nombre_clase == "Dog-without-Leash":
                    cajas_sueltos.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                elif nombre_clase == "dog leash":
                    cajas_correa.append({"bbox": [x1, y1, x2, y2], "confianza": conf})

        # Heurística: Si detecta una correa (dog leash) en la imagen, anulamos las cajas de perro suelto
        # que se superpongan o estén muy cerca, porque el modelo de Roboflow suele confundirse y predecir ambas.
        perros_finales = []
        
        # Primero agregamos los perros con correa (la correa manda)
        for c in cajas_correa:
            perros_finales.append({
                "bbox": c["bbox"],
                "confianza": round(c["confianza"], 3),
                "suelto": False
            })
            
        # Luego evaluamos los sueltos. Si se cruzan con un perro con correa, los ignoramos.
        for s in cajas_sueltos:
            sx1, sy1, sx2, sy2 = s["bbox"]
            scx, scy = (sx1 + sx2)/2, (sy1 + sy2)/2
            
            es_falso_suelto = False
            for c in cajas_correa:
                cx1, cy1, cx2, cy2 = c["bbox"]
                ccx, ccy = (cx1 + cx2)/2, (cy1 + cy2)/2
                dist = ((scx - ccx)**2 + (scy - ccy)**2)**0.5
                
                # Si el centro del perro "suelto" está muy cerca del centro de un perro "con correa" (ej. 150px)
                # significa que es el mismo perro y el modelo predijo ambas clases. La correa gana.
                if dist < 200:
                    es_falso_suelto = True
                    break
                    
            if not es_falso_suelto:
                perros_finales.append({
                    "bbox": s["bbox"],
                    "confianza": round(s["confianza"], 3),
                    "suelto": True
                })
                    
        return perros_finales
