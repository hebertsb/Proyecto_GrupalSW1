import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import json
from pathlib import Path
from ultralytics import YOLO

# ==========================================
# RUTAS PARA GOOGLE COLAB
# ==========================================
VIDEO_PATH = "/content/p2.mp4"
OUTPUT_VIDEO_PATH = "/content/resultado_final.mp4"

RESNET_MODEL_PATH = "/content/resnet50_dogs.pth"
RESNET_CLASSES_PATH = "/content/classes.json"
YOLO_CORREA_PATH = "/content/detector_correa.pt"
YOLO_HECES_PATH = "/content/feces_yolo.pt"

# ==========================================
# CLASIFICADOR DE RAZAS (ResNet50)
# ==========================================
class ResNetClassifier:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = Path(RESNET_MODEL_PATH)
        self.classes_path = Path(RESNET_CLASSES_PATH)
        
        if not self.model_path.exists() or not self.classes_path.exists():
            print("⚠️ Advertencia: No se encontro modelo ResNet. Omitiendo raza.")
            self.valido = False
            return
            
        with open(self.classes_path, "r", encoding="utf-8") as f:
            self.classes = json.load(f)
            
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.model = models.resnet50()
        num_ftrs = self.model.fc.in_features
        self.model.fc = nn.Linear(num_ftrs, len(self.classes))
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        self.valido = True
        print("✅ ResNet50 Cargado en", self.device)

    def predict(self, image_cv2):
        if not self.valido: return "Perro"
        img_rgb = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        tensor_img = self.transform(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            outputs = self.model(tensor_img)
            _, preds = torch.max(outputs, 1)
        raw_breed = self.classes[preds.item()]
        return raw_breed.split("-")[-1].replace("_", " ") if "-" in raw_breed else raw_breed

# ==========================================
# DETECTOR DE HECES Y POSTURA
# ==========================================
class PoopDetector:
    def __init__(self):
        if Path(YOLO_HECES_PATH).exists():
            self.model = YOLO(YOLO_HECES_PATH)
            print(f"✅ PoopDetector cargado")
        else:
            print("⚠️ PoopDetector no encontrado.")
            self.model = None

    def detect(self, image_cv2):
        heces = []
        if self.model:
            resultados = self.model(image_cv2, verbose=False)
            for box in resultados[0].boxes:
                conf = float(box.conf[0])
                if conf >= 0.50:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    nombre = self.model.names[int(box.cls[0])]
                    heces.append({"bbox": [x1, y1, x2, y2], "confianza": conf, "clase": nombre})
        return heces

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def main():
    print("Iniciando sistema de 4 IAs en Colab...")
    modelo_personas = YOLO("yolov8n.pt")
    
    if not Path(YOLO_CORREA_PATH).exists():
        print("ERROR: Falta el modelo de la correa.")
        return
    modelo_correa = YOLO(YOLO_CORREA_PATH)
    
    resnet_classifier = ResNetClassifier()
    poop_detector = PoopDetector()

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("ERROR: No se pudo leer el video.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    out = cv2.VideoWriter(OUTPUT_VIDEO_PATH, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    razas_por_id = {}
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Procesando frame {frame_count}/{total_frames}...")

        # 1. Humanos
        res_personas = modelo_personas.predict(frame, classes=[0], verbose=False)
        for box in res_personas[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, "Persona", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # 2. Perros y Correa
        res_correa = modelo_correa.track(frame, persist=True, verbose=False)
        if res_correa and res_correa[0].boxes is not None:
            for box in res_correa[0].boxes:
                nombre_clase = modelo_correa.names[int(box.cls[0])]
                track_id = int(box.id[0]) if box.id is not None else -1
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                # Clasificar raza
                if track_id not in razas_por_id and track_id != -1:
                    crop = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
                    if crop.size > 0:
                        razas_por_id[track_id] = resnet_classifier.predict(crop).title()
                
                raza_label = razas_por_id.get(track_id, "Perro")
                color = (0, 0, 255) if "without" in nombre_clase.lower() else (0, 255, 0)
                texto = f"{'ALERTA SUELTO' if color==(0,0,255) else 'SEGURO'}: {raza_label} #{track_id}"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, texto, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 3. Heces
        if frame_count % 5 == 0:
            for h in poop_detector.detect(frame):
                hx1, hy1, hx2, hy2 = h["bbox"]
                cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (0, 165, 255), 2)
                cv2.putText(frame, f"ALERTA: {h['clase']} ({h['confianza']:.2f})", (hx1, hy1-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

        out.write(frame)

    cap.release()
    out.release()
    print(f"\n✅ ¡Video procesado exitosamente! Descargalo de {OUTPUT_VIDEO_PATH}")

if __name__ == "__main__":
    main()
