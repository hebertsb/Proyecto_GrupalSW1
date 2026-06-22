import os
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

# v2 usa EfficientNet-B0; v1 usaba ResNet-18. Se detecta automáticamente por nombre de archivo.
MODEL_PATH_V2 = os.getenv("VEHICULO_EST_MODEL_PATH", "modelo_vehiculo_estacionamiento_v2.pth")
MODEL_PATH_V1 = "modelo_vehiculo_estacionamiento.pth"

_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# Orden alfabético ImageFolder: infraccion=0, normal=1
_CLASES = ["infraccion", "normal"]


def _construir_modelo_v2():
    from torchvision.models import efficientnet_b0
    m = efficientnet_b0(weights=None)
    m.classifier = nn.Sequential(nn.Dropout(p=0.3, inplace=True), nn.Linear(m.classifier[1].in_features, 2))
    return m

def _construir_modelo_v1():
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 2)
    return m


class VehiculoEstacionamientoClassifier:
    def __init__(self, model_path: str = None, umbral: float = 0.75):
        self.umbral = umbral
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Auto-detectar modelo disponible: v2 (EfficientNet) tiene prioridad
        if model_path is None:
            if Path(MODEL_PATH_V2).exists():
                model_path = MODEL_PATH_V2
            elif Path(MODEL_PATH_V1).exists():
                model_path = MODEL_PATH_V1
            else:
                raise FileNotFoundError(
                    f"No se encontró modelo de estacionamiento. "
                    f"Buscado: {MODEL_PATH_V2}, {MODEL_PATH_V1}"
                )

        ruta = Path(model_path)
        if not ruta.exists():
            raise FileNotFoundError(f"Modelo no encontrado en {ruta.resolve()}")

        es_v2 = "v2" in ruta.name
        modelo = _construir_modelo_v2() if es_v2 else _construir_modelo_v1()
        modelo.load_state_dict(torch.load(str(ruta), map_location=self.device))
        modelo.eval()
        self.modelo = modelo.to(self.device)
        print(f"✅ VehiculoEstacionamientoClassifier listo ({'EfficientNet-B0 v2' if es_v2 else 'ResNet-18 v1'}: {ruta.name})")

    def clasificar(self, img_bgr: np.ndarray) -> dict:
        """
        Recibe frame BGR completo (numpy). Devuelve:
          { "infraccion": bool, "confianza": float, "clase": "infraccion"|"normal" }
        """
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        tensor = _transform(img_rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.modelo(tensor)
            probs = torch.softmax(logits, dim=1)[0]

        idx = int(torch.argmax(probs).item())
        confianza = float(probs[idx].item())
        clase = _CLASES[idx]

        return {
            "infraccion": clase == "infraccion" and confianza >= self.umbral,
            "confianza":  round(confianza, 3),
            "clase":      clase,
        }
