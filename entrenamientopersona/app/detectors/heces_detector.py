import os
from ultralytics import YOLO

MODEL_PATH = os.getenv("HECES_MODEL_PATH", "modelo_heces.pt")

class HecesDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        try:
            self.model = YOLO(model_path)
            print("✅ HecesDetector listo")
        except Exception as e:
            print(f"⚠️ Error al cargar HecesDetector: {e}")
            self.model = None

    def detect(self, img, conf_min: float = 0.25) -> list:
        if self.model is None:
            return []
        results = self.model(img, verbose=False)
        heces = []
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < conf_min:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                clase_idx = int(box.cls[0])
                nombre_clase = self.model.names[clase_idx]
                
                heces.append({
                    "bbox": [x1, y1, x2, y2],
                    "confianza": round(conf, 3),
                    "clase": nombre_clase
                })
                print(f"[YOLO Heces] Detectó: {nombre_clase} ({conf:.2f})")
        return heces
