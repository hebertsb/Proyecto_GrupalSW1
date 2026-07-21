import os
from pathlib import Path

import numpy as np
from ultralytics import YOLO

MODEL_PATH = os.getenv("PLACA_MODEL_PATH", "modelo_placa.pt")


class PlacaDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        ruta = Path(model_path)
        if not ruta.exists():
            raise FileNotFoundError(
                f"Modelo de placas no encontrado en {ruta.resolve()}. "
                f"Entrena con entrenamiento_placa.ipynb y coloca modelo_placa.pt aquí."
            )
        self.model = YOLO(str(ruta))
        print(f"✅ PlacaDetector listo ({ruta.name})")

    def detect(self, img: np.ndarray, conf_min: float = 0.40) -> list[dict]:
        """
        Recibe imagen BGR (numpy). Devuelve lista de regiones de placa detectadas:
          [{"bbox": [x1, y1, x2, y2], "confianza": float, "crop": np.ndarray}]

        'crop' es el recorte BGR de la región de placa, listo para pasar a PlacaOCR.
        """
        resultados = self.model(img, conf=conf_min, verbose=False)
        placas = []
        for r in resultados:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                margin = 5
                crop = img[max(0, y1 - margin):y2 + margin,
                           max(0, x1 - margin):x2 + margin]
                placas.append({
                    "bbox":      [x1, y1, x2, y2],
                    "confianza": round(conf, 3),
                    "crop":      crop,
                })
        return placas
