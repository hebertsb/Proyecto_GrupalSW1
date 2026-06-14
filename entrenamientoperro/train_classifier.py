# train_classifier.py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import json
from pathlib import Path

# Configuración de rutas
DATA_DIR = Path(r"D:\SW1\entrenamientoperro\data\raw\stanford_dogs\Images")
MODEL_SAVE_PATH = Path("resnet50_dogs.pth")
CLASSES_SAVE_PATH = Path("classes.json")

def main():
    print("🚀 Iniciando preparación del entrenamiento...")
    
    # 1. Definir transformaciones de imágenes
    train_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406], 
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    # 2. Cargar Dataset
    if not DATA_DIR.exists():
        print(f"❌ Error: La ruta del dataset {DATA_DIR} no existe.")
        return
        
    dataset = datasets.ImageFolder(root=str(DATA_DIR), transform=train_transforms)
    print(f"📊 Dataset cargado: {len(dataset)} imágenes en {len(dataset.classes)} razas.")
    
    # Guardar mapeo de clases para inferencia
    with open(CLASSES_SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset.classes, f, indent=4)
    print(f"📁 Clases guardadas en {CLASSES_SAVE_PATH}")
    
    # 3. DataLoader
    train_loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=0)
    
    # 4. Configurar modelo ResNet50 pre-entrenado
    print("📥 Cargando ResNet50 pre-entrenado...")
    weights = models.ResNet50_Weights.DEFAULT
    model = models.resnet50(weights=weights)
    
    # Congelar capas inferiores para un entrenamiento rápido (Fine-Tuning de la cabeza)
    for param in model.parameters():
        param.requires_grad = False
        
    # Reemplazar la capa completamente conectada (fc)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, len(dataset.classes))
    
    # Configurar dispositivo (GPU si está disponible)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"💻 Entrenando en: {device}")
    
    # 5. Pérdida y optimizador
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.fc.parameters(), lr=0.001)
    
    # 6. Bucle de entrenamiento simplificado (1 epoch de ejemplo para verificar funcionamiento)
    # Puedes cambiar epochs a más (ej. 5 o 10) para mayor precisión.
    epochs = 1
    model.train()
    
    print("🏋️ Comienza el entrenamiento...")
    for epoch in range(epochs):
        running_loss = 0.0
        running_corrects = 0
        
        for i, (inputs, labels) in enumerate(train_loader):
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            _, preds = torch.max(outputs, 1)
            
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)
            
            if (i + 1) % 10 == 0:
                print(f"   [Epoch {epoch+1}/{epochs}] Batch {i+1}/{len(train_loader)} - Loss: {loss.item():.4f}")
                
        epoch_loss = running_loss / len(dataset)
        epoch_acc = running_corrects.double() / len(dataset)
        print(f"🌟 Epoch {epoch+1} completada - Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")
        
    # 7. Guardar pesos del modelo entrenado
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print(f"💾 Pesos del modelo guardados con éxito en {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    main()
