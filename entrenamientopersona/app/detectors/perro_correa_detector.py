import os
import cv2
from ultralytics import YOLO

MODEL_PATH = os.getenv("PERRO_CORREA_MODEL_PATH", "modelo_correa_nuevo.pt")
BASE_MODEL_PATH = "yolov8n.pt"

class PerroCorreaDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        try:
            self.model_custom = YOLO(model_path)
            self.model_base = YOLO(BASE_MODEL_PATH)
            print("✅ PerroCorreaDetector (proximidad) listo")
        except Exception as e:
            print(f"⚠️ Error al cargar PerroCorreaDetector: {e}")
            self.model_custom = None
            self.model_base = None

    def detect(self, img, conf_min: float = 0.30) -> list:
        if self.model_custom is None or self.model_base is None:
            return []

        results_custom = self.model_custom(img, verbose=False, conf=conf_min)
        results_base   = self.model_base(img, verbose=False, conf=0.30)

        cajas_perros   = []
        cajas_personas = []

        for r in results_custom:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf  = float(box.conf[0])
                clase = r.names[int(box.cls[0])].lower()
                cajas_perros.append({"bbox": [x1, y1, x2, y2], "confianza": conf, "clase": clase})

        for r in results_base:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                if int(box.cls[0]) == 0:
                    cajas_personas.append({"bbox": [x1, y1, x2, y2]})

        perros_finales = []
        for p in cajas_perros:
            x1, y1, x2, y2 = p["bbox"]
            px, py = (x1 + x2) / 2, (y1 + y2) / 2

            # Criterio único: persona cerca (≤300px) = perro con dueño = correa
            tiene_correa = False
            for per in cajas_personas:
                perx = (per["bbox"][0] + per["bbox"][2]) / 2
                pery = (per["bbox"][1] + per["bbox"][3]) / 2
                if ((px - perx) ** 2 + (py - pery) ** 2) ** 0.5 < 300:
                    tiene_correa = True
                    break

            print(f"[DEBUG perro] clase={p['clase']} conf={p['confianza']:.2f} tiene_correa={tiene_correa}")
            perros_finales.append({
                "bbox": p["bbox"],
                "confianza": round(p["confianza"], 3),
                "suelto": not tiene_correa,
            })

        return perros_finales
