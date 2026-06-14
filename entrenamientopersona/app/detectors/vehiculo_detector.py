from ultralytics import YOLO

VEHICLE_CLASSES = {2: "auto", 3: "moto", 5: "bus", 7: "camion"}


class VehiculoDetector:
    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model = YOLO(model_path)
        print("✅ VehiculoDetector listo (yolov8n clases 2,3,5,7)")

    def detect(self, img, conf_min: float = 0.35) -> list:
        results = self.model(img, verbose=False)
        vehiculos = []
        for r in results:
            for box in r.boxes:
                clase_id = int(box.cls[0])
                if clase_id not in VEHICLE_CLASSES:
                    continue
                conf = float(box.conf[0])
                if conf < conf_min:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                vehiculos.append({
                    "bbox": [x1, y1, x2, y2],
                    "confianza": round(conf, 3),
                    "tipo": VEHICLE_CLASSES[clase_id],
                })
        return vehiculos
