from ultralytics import YOLO


class PersonaDetector:
    CLASE_ID = 0  # 'person' en COCO

    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model = YOLO(model_path)
        print("✅ PersonaDetector listo (yolov8n clase 0)")

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
