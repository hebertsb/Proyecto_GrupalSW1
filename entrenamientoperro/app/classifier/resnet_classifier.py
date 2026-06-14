import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import cv2
import json
from pathlib import Path

class ResNetClassifier:
    def __init__(self, model_path: str = r"D:\SW1\entrenamientoperro\models\resnet50_dogs.pth", 
                 classes_path: str = r"D:\SW1\entrenamientoperro\models\classes.json"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = Path(model_path)
        self.classes_path = Path(classes_path)
        
        if not self.model_path.exists() or not self.classes_path.exists():
            raise FileNotFoundError("Model weights or classes mapping not found.")
            
        with open(self.classes_path, "r", encoding="utf-8") as f:
            self.classes = json.load(f)
            
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        self.model = models.resnet50()
        num_ftrs = self.model.fc.in_features
        self.model.fc = nn.Linear(num_ftrs, len(self.classes))
        
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def predict(self, image_cv2) -> str:
        img_rgb = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        tensor_img = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(tensor_img)
            _, preds = torch.max(outputs, 1)
            idx = preds.item()
            
        raw_breed = self.classes[idx]
        clean_breed = raw_breed.split("-")[-1].replace("_", " ") if "-" in raw_breed else raw_breed
        return clean_breed
