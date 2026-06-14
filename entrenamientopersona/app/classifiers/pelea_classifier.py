import os
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

MODEL_PATH = os.getenv("PELEA_MODEL_PATH", "modelo_pelea.pth")

_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# Índice 0 = Fight, 1 = NonFight (orden alfabético ImageFolder)
_CLASES = ["Fight", "NonFight"]


class PeleaClassifier:
    def __init__(self, model_path: str = MODEL_PATH, umbral: float = 0.75):
        self.umbral = umbral
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        modelo = models.resnet18(weights=None)
        modelo.fc = nn.Linear(modelo.fc.in_features, 2)

        ruta = Path(model_path)
        if not ruta.exists():
            raise FileNotFoundError(f"modelo_pelea.pth no encontrado en {ruta.resolve()}")

        modelo.load_state_dict(torch.load(str(ruta), map_location=self.device))
        modelo.eval()
        self.modelo = modelo.to(self.device)

    def clasificar(self, img_bgr: np.ndarray) -> dict:
        """
        Recibe frame BGR (numpy). Devuelve:
          { "pelea": bool, "confianza": float, "clase": "Fight"|"NonFight" }
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
            "pelea": clase == "Fight" and confianza >= self.umbral,
            "confianza": round(confianza, 3),
            "clase": clase,
        }
