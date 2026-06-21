import os
import json
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

MODEL_PATH = os.getenv("DOGS_RESNET_PATH", "resnet50_dogs.pth")
CLASSES_PATH = os.getenv("DOGS_CLASSES_PATH", "classes.json")

_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

class PerroRazaClassifier:
    def __init__(self, model_path: str = MODEL_PATH, classes_path: str = CLASSES_PATH):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ruta_modelo = Path(model_path)
        ruta_clases = Path(classes_path)
        
        if not ruta_modelo.exists() or not ruta_clases.exists():
            raise FileNotFoundError(f"Archivos de ResNet no encontrados en {ruta_modelo} o {ruta_clases}")
            
        with open(ruta_clases, "r", encoding="utf-8") as f:
            self.classes = json.load(f)
            
        self.modelo = models.resnet50(weights=None)
        num_ftrs = self.modelo.fc.in_features
        self.modelo.fc = nn.Linear(num_ftrs, len(self.classes))
        
        self.modelo.load_state_dict(torch.load(str(ruta_modelo), map_location=self.device))
        self.modelo.eval()
        self.modelo = self.modelo.to(self.device)

    def clasificar(self, img_bgr: np.ndarray) -> dict:
        """
        Recibe SOLO el recorte (crop) del perro en BGR.
        """
        if img_bgr.size == 0:
            return {"raza": "Perro Desconocido", "confianza": 0.0}
            
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        tensor = _transform(img_rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.modelo(tensor)
            probs = torch.softmax(logits, dim=1)[0]

        idx = int(torch.argmax(probs).item())
        confianza = float(probs[idx].item())
        
        raw_breed = self.classes[idx]
        clean_breed = raw_breed.split("-")[-1].replace("_", " ") if "-" in raw_breed else raw_breed

        return {
            "raza": clean_breed.title(),
            "confianza": round(confianza, 3),
        }
