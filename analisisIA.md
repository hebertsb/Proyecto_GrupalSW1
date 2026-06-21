import torch
import torch.nn as nn
from torchvision import datasets, transforms, models

# 1. Transforms (mismo que el tuyo)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# 2. Cargar dataset
train_dataset = datasets.ImageFolder('/content/dataset_vehiculos_acciones/train', transform=transform)
val_dataset   = datasets.ImageFolder('/content/dataset_vehiculos_acciones/val',   transform=transform)

train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader   = torch.utils.data.DataLoader(val_dataset,   batch_size=32)

# 3. CARGAR modelo_condominio_final.pt como base
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

modelo = models.resnet18(weights=None)
modelo.fc = nn.Linear(512, 4)                          # arquitectura del modelo base (4 clases)
modelo.load_state_dict(torch.load('modelo_condominio_final.pt', map_location=device))

# 4. Reemplazar fc para las nuevas clases de acción
NUM_CLASES = 4  # mal_estacionado, bien_estacionado, invadiendo_paso, zona_prohibida
modelo.fc = nn.Linear(512, NUM_CLASES)
modelo = modelo.to(device)

# 5. Entrenar (capas congeladas opcionales para dataset pequeño)
# Opcional: congelar capas base si tiene pocas imágenes
for param in list(modelo.parameters())[:-2]:
    param.requires_grad = False   # solo entrena la última capa

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, modelo.parameters()), lr=0.0001)

# 6. Loop de entrenamiento
for epoch in range(20):
    modelo.train()
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        loss = criterion(modelo(imgs), labels)
        loss.backward()
        optimizer.step()

# 7. Guardar
torch.save(modelo.state_dict(), 'modelo_vehiculo_acciones.pth')
!cp modelo_vehiculo_acciones.pth /content/drive/MyDrive/


------------------

# vehiculo_accion_classifier.py
_CLASES = ["bien_estacionado", "invadiendo_paso", "mal_estacionado", "zona_prohibida"]
# (orden alfabético — ImageFolder los ordena así)

class VehiculoAccionClassifier:
    def __init__(self, model_path="modelo_vehiculo_acciones.pth", umbral=0.75):
        modelo = models.resnet18(weights=None)
        modelo.fc = nn.Linear(512, 4)
        modelo.load_state_dict(torch.load(model_path, map_location="cpu"))
        modelo.eval()
        self.modelo = modelo

    def clasificar(self, img_bgr):
        # mismo código que PeleaClassifier.clasificar()
        ...
        return {"accion": clase, "confianza": confianza, "alerta": clase != "bien_estacionado"}

Paso 3 — Integrar en api.py (igual que PeleaClassifier)