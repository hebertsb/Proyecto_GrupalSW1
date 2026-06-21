from ultralytics import YOLO


class PersonaDetector:
    CLASE_ID = 0  # 'person' en COCO

    def __init__(self, model_path: str = None):
        import os
        if model_path is None:
            model_path = os.getenv("PERSONA_MODEL_PATH", "modelo_condominio_final.pt")
            if not __import__("pathlib").Path(model_path).exists():
                model_path = "yolov8n.pt"
        try:
            self.model = YOLO(model_path)
            print(f"✅ PersonaDetector listo ({model_path} clase 0)")
        except Exception:
            print(f"⚠️  No se pudo cargar {model_path}, usando yolov8n.pt")
            self.model = YOLO("yolov8n.pt")
            print("✅ PersonaDetector listo (yolov8n.pt clase 0)")

    def detect(self, img, conf_min: float = 0.35) -> list:
        results = self.model(img, verbose=False)
        personas = []
        for r in results:
            for box in r.boxes:
                if int(box.cls[0]) != self.CLASE_ID:
                    continue
                conf = float(box.conf[0])
                if conf < conf_min:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                personas.append({"bbox": [x1, y1, x2, y2], "confianza": round(conf, 3)})
        return personas
