# Guía de Estudio — Modelos de IA del Sistema SIVIC

Esta guía explica cómo funcionan los modelos de inteligencia artificial del sistema, desde el entrenamiento hasta la detección en tiempo real. Está pensada para que cualquier integrante del equipo pueda entender y explicar el sistema en la defensa.

---

## Índice

1. [¿Qué es ResNet18?](#1-qué-es-resnet18)
2. [¿Qué es Transfer Learning?](#2-qué-es-transfer-learning)
3. [Pipeline completo de entrenamiento](#3-pipeline-completo-de-entrenamiento)
4. [Etapa 1 — Modelo base ImageNet](#4-etapa-1--modelo-base-imagenet)
5. [Etapa 2 — Clasificador de condominio (4 clases)](#5-etapa-2--clasificador-de-condominio-4-clases)
6. [Etapa 3 — Clasificador de peleas](#6-etapa-3--clasificador-de-peleas)
7. [¿Cómo aprende el modelo de los videos?](#7-cómo-aprende-el-modelo-de-los-videos)
8. [Detección en producción — flujo completo](#8-detección-en-producción--flujo-completo)
9. [Detección de personas con YOLO](#9-detección-de-personas-con-yolo)
10. [Conteo y clasificación de nivel](#10-conteo-y-clasificación-de-nivel)
11. [¿Dónde está cada archivo?](#11-dónde-está-cada-archivo)
12. [Preguntas frecuentes de defensa](#12-preguntas-frecuentes-de-defensa)

---

## 1. ¿Qué es ResNet18?

ResNet18 es una **red neuronal convolucional** (CNN) creada por Microsoft Research en 2015. Es una de las arquitecturas más usadas para clasificación de imágenes.

### ¿Qué significa "18"?

18 capas de profundidad. Cada capa aprende a detectar patrones más complejos:

```
Capa 1-3:   detecta bordes horizontales, verticales, diagonales
Capa 4-7:   detecta texturas (piel, tela, metal, asfalto)
Capa 8-14:  detecta formas (ruedas, caras, brazos, ventanas)
Capa 15-17: detecta objetos completos (persona parada, auto, perro)
Capa 18:    capa final (fc) → decide la clase: persona/mascota/vacío/vehículo
```

### La capa final (fc — fully connected)

Esta es la única capa que cambiamos cuando adaptamos el modelo para nuestras clases:

```python
# ResNet18 original: clasifica 1000 categorías ImageNet
modelo.fc = nn.Linear(512, 1000)

# Nuestro cambio — 4 clases condominio:
modelo.fc = nn.Linear(512, 4)

# Nuestro cambio — 2 clases pelea:
modelo.fc = nn.Linear(512, 2)
```

`512` es el número de "características" que la red detecta antes de la decisión final. Ese número no cambia — solo cambiamos cuántas clases de salida queremos.

---

## 2. ¿Qué es Transfer Learning?

Transfer Learning significa **reutilizar conocimiento de un entrenamiento anterior** en lugar de empezar desde cero.

### Analogía simple

Imagina que sabes inglés perfectamente. Si ahora aprendes portugués, no tienes que volver a aprender qué es un sustantivo, un verbo, cómo funciona la gramática — solo adaptas lo que ya sabes. Tardas meses, no años.

Con los modelos pasa igual:

- ResNet18 entrenado en ImageNet ya "sabe" qué son bordes, texturas, formas, objetos.
- Cuando lo fine-tuneamos con nuestras fotos, solo necesita aprender "en este condominio, ESTO es una persona, ESTO es un auto".
- Sin transfer learning: necesitaríamos millones de fotos y semanas de GPU.
- Con transfer learning: 9489 fotos y ~30 minutos en Colab.

### ¿Por qué funciona?

Las capas intermedias de ResNet18 aprenden características **universales** que sirven para cualquier tipo de imagen. Solo la capa final (fc) es específica de las clases. Por eso solo reemplazamos esa última capa y re-entrenamos.

---

## 3. Pipeline completo de entrenamiento

```
┌──────────────────────────────────────────────────────────────────┐
│  ETAPA 1 — ResNet18 base (ImageNet)                              │
│                                                                  │
│  Quién lo entrenó: Microsoft Research / PyTorch                  │
│  Dataset: ImageNet — 1.2 millones de imágenes, 1000 categorías  │
│  Tiempo de entrenamiento: semanas en cientos de GPUs             │
│  Archivo: resnet18-f37072fd.pth (descarga automática PyTorch)   │
│  Resultado: red que entiende el mundo visual en general          │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │  pretrained=True  →  PyTorch descarga los pesos
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  ETAPA 2 — Clasificador condominio (nuestro entrenamiento #1)    │
│                                                                  │
│  Notebook: entrenamiento_condominio.ipynb                        │
│  Dataset: dataset_condominio.zip (Google Drive)                  │
│    train/mascotas/   ≈ 2300 imágenes                            │
│    train/personas/   ≈ 2400 imágenes                            │
│    train/vacios/     ≈ 2400 imágenes                            │
│    train/vehiculos/  ≈ 2400 imágenes                            │
│    val/              ≈  454 imágenes (validación)               │
│                                                                  │
│  Qué hicimos:                                                    │
│    1. Cargamos ResNet18 con pesos ImageNet                       │
│    2. Reemplazamos fc: 1000 clases → 4 clases                   │
│    3. Entrenamos 20 épocas con Adam lr=0.0001                   │
│    4. Guardamos el modelo resultante                             │
│                                                                  │
│  Resultado: modelo_condominio_final.pt                           │
│  → sabe identificar personas/mascotas/vehículos/vacío           │
│    en el ambiente visual específico de nuestras cámaras          │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │  cargamos modelo_condominio_final.pt como base
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  ETAPA 3 — Clasificador de peleas (nuestro entrenamiento #2)     │
│                                                                  │
│  Notebook: entrenamiento_pelea.ipynb                             │
│  Dataset: Kaggle real-life-violence-situations-dataset           │
│    Violence/    → 1000 videos de peleas reales                  │
│    NonViolence/ → 1000 videos de situaciones normales           │
│                                                                  │
│  Proceso de extracción de frames:                                │
│    FRAMES_POR_VIDEO = 10                                         │
│    Por cada video → extrae 10 fotogramas                        │
│    Violence:    1000 videos × 10 = 10,000 imágenes Fight        │
│    NonViolence: 1000 videos × 10 = 10,000 imágenes NonFight     │
│    TOTAL: 20,000 imágenes de entrenamiento                       │
│                                                                  │
│  Qué hicimos:                                                    │
│    1. Cargamos modelo_condominio_final.pt                        │
│    2. Reemplazamos fc: 4 clases → 2 clases (Fight/NonFight)     │
│    3. Re-entrenamos con el dataset de violencia                  │
│    4. Guardamos el modelo final                                  │
│                                                                  │
│  Resultado: modelo_pelea.pth                                     │
│  → detecta peleas en frames de video en tiempo real              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Etapa 1 — Modelo base ImageNet

No entrenamos esto nosotros. PyTorch lo descarga automáticamente con `pretrained=True`.

```python
modelo = models.resnet18(pretrained=True)
# Esto descarga resnet18-f37072fd.pth desde servidores de PyTorch
# El archivo pesa ~44 MB y contiene 11 millones de parámetros
```

Este archivo (`resnet18-f37072fd.pth`) aparece en el Drive porque Colab lo descargó durante el entrenamiento y lo guardamos como respaldo. **No es nuestro modelo** — es el punto de partida oficial de PyTorch.

---

## 5. Etapa 2 — Clasificador de condominio (4 clases)

**Archivo notebook:** `entrenamientopersona/entrenamiento_condominio.ipynb`

### ¿Qué hace exactamente el notebook?

```python
# Paso 1: Monta Google Drive para acceder al dataset
from google.colab import drive
drive.mount('/content/drive')

# Paso 2: Descomprime el dataset
zip_path = '/content/drive/MyDrive/dataset_condominio.zip'
extract_path = '/content/dataset'
# → crea /content/dataset/dataset_condominio/train/ y /val/

# Paso 3: Define transformaciones de imagen
transform = transforms.Compose([
    transforms.Resize((224, 224)),         # todas las imágenes al mismo tamaño
    transforms.RandomHorizontalFlip(),     # espeja fotos aleatoriamente (más datos)
    transforms.RandomRotation(15),         # gira un poco (más variedad)
    transforms.ColorJitter(...),           # varía brillo/contraste (simula condiciones)
    transforms.ToTensor(),                 # convierte a tensor numérico
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])  # normaliza
])
# Las transformaciones aleatorias multiplican artificialmente la variedad del dataset

# Paso 4: Carga el dataset automáticamente por carpetas
train_dataset = datasets.ImageFolder('/content/dataset/dataset_condominio/train', transform=transform)
# ImageFolder lee el nombre de la carpeta como clase:
#   carpeta mascotas/  → clase 0
#   carpeta personas/  → clase 1
#   carpeta vacios/    → clase 2
#   carpeta vehiculos/ → clase 3
# (orden alfabético siempre)

# Paso 5: Crea el modelo
modelo = models.resnet18(pretrained=True)   # carga pesos ImageNet
modelo.fc = nn.Linear(512, 4)               # reemplaza última capa para 4 clases
modelo = modelo.to(device)

# Paso 6: Configura el entrenamiento
criterion = nn.CrossEntropyLoss()           # mide qué tan equivocado está
optimizer = torch.optim.Adam(modelo.parameters(), lr=0.0001)

# Paso 7: Entrena
for epoch in range(20):
    for imgs, labels in train_loader:
        optimizer.zero_grad()
        outputs = modelo(imgs)     # el modelo predice
        loss = criterion(outputs, labels)  # calcula error
        loss.backward()            # calcula cómo corregir cada parámetro
        optimizer.step()           # aplica la corrección

# Paso 8: Guarda
torch.save(modelo.state_dict(), 'modelo_condominio.pt')
# !cp modelo_condominio.pt /content/drive/MyDrive/modelo_condominio_final.pt
```

### Resultado: 9489 imágenes train, 454 validación

El output que vimos en el notebook:
```
Clases detectadas: ['mascotas', 'personas', 'vacios', 'vehiculos']
Imágenes de entrenamiento: 9489
Imágenes de validación: 454
```

Y al probar con una foto:
```
ANÁLISIS DE CONFIANZA:
Persona:  97.53%
Mascota:   0.57%
Vehículo:  1.60%
Vacío:     0.30%
PREDICCIÓN FINAL: PERSONAS
```

---

## 6. Etapa 3 — Clasificador de peleas

**Archivo notebook:** `entrenamientopersona/entrenamiento_pelea.ipynb`

**Archivo modelo:** `entrenamientopersona/modelo_pelea.pth`

### ¿Por qué usar videos y no fotos?

Las peleas son eventos dinámicos. Un frame aislado puede ser ambiguo (dos personas abrazadas vs peleando se ven similar). Por eso:

1. Usamos videos del dataset Kaggle (situaciones de violencia real grabadas)
2. Extraemos múltiples frames por video (10 frames distribuidos a lo largo del video)
3. El modelo aprende patrones visuales típicos de peleas: posturas, proximidad entre personas, movimiento capturado en el frame

### Proceso de extracción de frames

```python
FRAMES_POR_VIDEO = 10

def extraer_frames(ruta_video, n_frames=FRAMES_POR_VIDEO):
    cap = cv2.VideoCapture(ruta_video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = np.linspace(0, total-1, n_frames, dtype=int)
    # linspace distribuye los índices uniformemente a lo largo del video
    # Ejemplo video de 300 frames → extrae frames en posiciones [0, 33, 66, 99, ...]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    cap.release()
    return frames
```

Esto produce:
```
Violence/    1000 videos × 10 frames = 10,000 imágenes  → clase "Fight"
NonViolence/ 1000 videos × 10 frames = 10,000 imágenes  → clase "NonFight"
Total: 20,000 imágenes de entrenamiento
```

### ¿Cómo el modelo aprende a distinguir peleas?

El modelo ve miles de veces imágenes de peleas reales y aprende patrones como:
- Personas muy próximas entre sí en postura agresiva
- Brazos extendidos en movimiento (aunque sea un instante congelado)
- Posturas de caída o desequilibrio
- Grupos de personas alrededor de un punto central

Y aprende que las situaciones normales tienen:
- Personas caminando o paradas de forma independiente
- Mayor distancia entre personas
- Posturas relajadas

---

## 7. ¿Cómo aprende el modelo de los videos?

### El proceso de entrenamiento (simplificado)

1. **Forward pass** — el modelo ve una imagen y predice una clase
2. **Loss** — calculamos qué tan equivocado estuvo (CrossEntropyLoss)
3. **Backward pass** — calculamos cómo ajustar cada uno de los 11 millones de parámetros para equivocarse menos
4. **Optimizer step** — aplicamos los ajustes (Adam, lr=0.0001)
5. Repetimos esto miles de veces (una época = ver todo el dataset una vez)

### ¿Qué son los "parámetros"?

ResNet18 tiene ~11 millones de números (pesos). Cada número controla qué tan importante es una característica visual para tomar la decisión. Al entrenar, estos 11 millones de números se van ajustando milímetro a milímetro para que el modelo se equivoque menos y menos.

### ¿Qué es lr=0.0001 (learning rate)?

El "paso" con el que se ajustan los parámetros en cada iteración. Si es muy grande, el modelo oscila y nunca converge. Si es muy pequeño, tarda muchísimo. 0.0001 es un valor estándar y seguro para fine-tuning.

### ¿Qué es una época?

Una pasada completa por todo el dataset. Si tenemos 20,000 imágenes y batch_size=64, una época son 313 iteraciones. Entrenamos 20 épocas → el modelo ve cada imagen 20 veces.

### ¿Qué es batch_size=64?

En lugar de actualizar los parámetros después de cada imagen (lento e inestable), actualizamos después de ver 64 imágenes a la vez. Es más eficiente y estable.

---

## 8. Detección en producción — flujo completo

Una vez entrenado, el modelo funciona así en el sistema real:

```
Cámara IP / RTSP / MJPEG
          │
          ▼
┌─────────────────────┐
│  OpenCV              │
│  cap.read() → frame  │  Frame BGR numpy array, ej: (480, 640, 3)
└──────────┬──────────┘
           │
           ▼
┌───────────────────────────────────┐
│  Servidor IA (entrenamientopersona/api.py)  │
│                                   │
│  PersonaDetector.detectar(frame)  │──→ lista de bounding boxes de personas
│  PeleaClassifier.clasificar(frame)│──→ { "pelea": bool, "confianza": 0.87 }
└──────────┬────────────────────────┘
           │
           │  POST /api/camaras/<id>/analizar_ia/
           ▼
┌───────────────────────────────────┐
│  Backend Django (sivic_backend)   │
│                                   │
│  Cuenta personas detectadas       │
│  Calcula nivel: normal/sospechoso/crítico
│  Si hay pelea → crea Evento en DB │
│  Emite WebSocket a todos los      │
│  guardias conectados              │
└──────────┬────────────────────────┘
           │
           ▼
┌─────────────────────┐   ┌─────────────────────┐
│  Angular Web         │   │  Flutter App         │
│  Badge campana       │   │  Notificación push   │
│  Panel NVR actualiza │   │  Alerta en pantalla  │
└─────────────────────┘   └─────────────────────┘
```

### Archivo clave: `entrenamientopersona/app/classifiers/pelea_classifier.py`

```python
MODEL_PATH = os.getenv("PELEA_MODEL_PATH", "modelo_pelea.pth")

class PeleaClassifier:
    def __init__(self, model_path=MODEL_PATH, umbral=0.75):
        # Reconstruye la arquitectura ResNet18 con 2 clases
        modelo = models.resnet18(weights=None)
        modelo.fc = nn.Linear(modelo.fc.in_features, 2)
        # Carga los pesos entrenados
        modelo.load_state_dict(torch.load(str(ruta), map_location=self.device))
        modelo.eval()   # modo inferencia (no entrenamiento)
        self.modelo = modelo

    def clasificar(self, img_bgr):
        # 1. Convierte BGR (OpenCV) → RGB (PyTorch espera RGB)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        # 2. Aplica las mismas transformaciones del entrenamiento
        tensor = _transform(img_rgb).unsqueeze(0)
        # 3. Pasa por la red
        with torch.no_grad():
            logits = self.modelo(tensor)
            probs = torch.softmax(logits, dim=1)[0]
        # 4. Decide
        idx = int(torch.argmax(probs).item())
        confianza = float(probs[idx].item())
        clase = ["Fight", "NonFight"][idx]

        return {
            "pelea": clase == "Fight" and confianza >= self.umbral,
            "confianza": round(confianza, 3),
            "clase": clase,
        }
```

**Umbral 0.75**: el modelo solo reporta pelea si está 75% o más seguro. Evita falsos positivos (reportar pelea cuando no hay).

### ¿Por qué `weights=None` en producción pero `pretrained=True` en entrenamiento?

- **Entrenamiento**: `pretrained=True` carga los pesos ImageNet como punto de partida
- **Producción**: `weights=None` crea la arquitectura vacía, luego `load_state_dict()` carga NUESTROS pesos ya entrenados (que incluyen todo lo aprendido de ImageNet + condominio + peleas)

---

## 9. Detección de personas con YOLO

Para detectar personas y vehículos usamos un modelo diferente: **YOLOv8n** (You Only Look Once, versión 8, nano).

A diferencia de ResNet18 que clasifica toda la imagen, YOLO **localiza objetos** dentro de la imagen dibujando bounding boxes.

**Archivo:** `entrenamientopersona/app/detectors/persona_detector.py`

```python
from ultralytics import YOLO

class PersonaDetector:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")   # modelo COCO estándar, 80 clases

    def detectar(self, frame_bgr):
        resultados = self.model(frame_bgr, verbose=False)
        detecciones = []
        for r in resultados:
            for box in r.boxes:
                clase_id = int(box.cls[0])
                if clase_id == 0:   # clase 0 en COCO = persona
                    x1,y1,x2,y2 = box.xyxy[0].tolist()
                    detecciones.append({
                        "clase": "persona",
                        "confianza": float(box.conf[0]),
                        "bbox": [x1, y1, x2, y2]
                    })
        return detecciones
```

**Importante:** `yolov8n.pt` es el modelo oficial de Ultralytics, entrenado en el dataset COCO (80 categorías de objetos comunes). **No es un modelo que entrenamos nosotros** — lo usamos directamente porque ya detecta personas y vehículos con alta precisión.

### YOLO vs ResNet18

| | YOLO | ResNet18 |
|---|---|---|
| Tarea | Detección (dónde está) | Clasificación (qué es) |
| Salida | Bounding boxes + clases | Una clase para toda la imagen |
| Uso en SIVIC | Detectar y contar personas | Clasificar si hay pelea |
| Modelo | YOLOv8n.pt (COCO oficial) | modelo_pelea.pth (nuestro) |

---

## 10. Conteo y clasificación de nivel

Una vez que YOLO detecta las personas en el frame, el backend cuenta cuántas hay y asigna un nivel de alerta.

**Archivo:** `apps/sivic_backend/camaras/views.py`

```python
# Filtra solo las detecciones de personas (no vehículos u otras cosas)
_personas_det = [
    d for d in resultado.get('detecciones', [])
    if d.get('clase') in ('persona', 'person')
]

# Cuenta cuántas personas hay
_conteo_personas = len(_personas_det)

# Asigna nivel según cantidad
if _conteo_personas >= 6:
    _nivel = 'critico'       # 6 o más personas → CRÍTICO (rojo)
elif _conteo_personas >= 3:
    _nivel = 'sospechoso'    # 3 a 5 personas → SOSPECHOSO (amarillo)
else:
    _nivel = 'normal'        # 0 a 2 personas → NORMAL (verde)

resultado['conteo_personas'] = _conteo_personas
resultado['nivel'] = _nivel
```

Estos valores se muestran en el panel web (Angular) con un badge de color sobre cada celda de cámara:

```
0-2 personas → badge verde  "2 · NORMAL"
3-5 personas → badge amarillo "4 · SOSPECHOSO"
6+  personas → badge rojo parpadeante "7 · CRÍTICO"
```

---

## 11. ¿Dónde está cada archivo?

```
SmartCondominium/
│
├── entrenamientopersona/                    ← Servidor IA independiente (FastAPI)
│   │
│   ├── modelo_pelea.pth                     ← Modelo entrenado (Fight/NonFight)
│   │                                           Etapa 3 del pipeline
│   │                                           44 MB, ResNet18 2 clases
│   │
│   ├── yolov8n.pt                           ← Modelo YOLO oficial (COCO 80 clases)
│   │                                           6.4 MB, detecta personas/vehículos
│   │
│   ├── entrenamiento_condominio.ipynb       ← Notebook Colab Etapa 2
│   │                                           Entrena modelo 4 clases condominio
│   │
│   ├── entrenamiento_pelea.ipynb            ← Notebook Colab Etapa 3
│   │                                           Descarga Kaggle, extrae frames,
│   │                                           entrena Fight/NonFight
│   │
│   ├── api.py                               ← FastAPI: endpoint POST /analizar
│   │                                           Recibe frame → devuelve detecciones
│   │
│   ├── app/
│   │   ├── detectors/
│   │   │   ├── persona_detector.py          ← Usa yolov8n.pt, filtra clase 0
│   │   │   └── vehiculo_detector.py         ← Usa yolov8n.pt, filtra clases 2,3,5,7
│   │   │
│   │   └── classifiers/
│   │       └── pelea_classifier.py          ← Usa modelo_pelea.pth, umbral 0.75
│   │
│   └── requirements.txt                     ← ultralytics, torch, torchvision, fastapi
│
└── apps/sivic_backend/                      ← Backend principal (Django)
    └── camaras/
        └── views.py                         ← analizar_ia(): llama al servidor IA,
                                                cuenta personas, asigna nivel,
                                                emite WebSocket
```

### Modelo que NO está en el repo

| Archivo | Por qué no está | Dónde conseguirlo |
|---|---|---|
| `modelo_condominio_final.pt` | 44 MB, base para entrenar pero no usado en producción | Google Drive del proyecto |
| `resnet18-f37072fd.pth` | Modelo oficial PyTorch, no es nuestro | Se descarga auto con `pretrained=True` |

---

## 12. Preguntas frecuentes de defensa

**P: ¿Por qué usaron ResNet18 y no una red más grande como ResNet50 o VGG?**

R: ResNet18 es un buen equilibrio entre precisión y velocidad. Para clasificación binaria (pelea/no pelea) con 20,000 imágenes, una red más grande no mejora significativamente la precisión pero es más lenta para inferencia en tiempo real. Necesitamos procesar frames cada 2 segundos por cámara.

---

**P: ¿Por qué YOLO para personas y ResNet18 para peleas? ¿No podrían hacer todo con un solo modelo?**

R: Son tareas distintas:
- YOLO hace **detección** (encuentra dónde están los objetos en la imagen, múltiples objetos simultáneamente).
- ResNet18 hace **clasificación** (decide qué sucede en toda la imagen).
Para contar cuántas personas hay necesitamos YOLO (bounding boxes individuales). Para detectar peleas, basta con clasificar la escena completa.

---

**P: ¿Qué tan preciso es el modelo de peleas?**

R: El dataset Kaggle real-life-violence-situations-dataset tiene un balance perfecto (1000 Fight / 1000 NonFight). Con fine-tuning de ResNet18, los modelos similares en literatura alcanzan ~90-95% de precisión en validación. Usamos un umbral de 0.75 (75% de confianza mínima) para reducir falsos positivos.

---

**P: ¿El sistema analiza video en tiempo real o fotos aisladas?**

R: Analiza frames individuales (fotografías), no video continuo. El backend llama al servidor IA cada 2 segundos con un frame capturado de la cámara. La detección temporal (¿lleva tiempo ahí?) la maneja el sistema de reglas del backend (ejemplo: merodeo = misma persona detectada por 90 análisis consecutivos ≈ 3 minutos).

---

**P: ¿Cómo se comunica el servidor IA (Python/FastAPI) con el backend (Django)?**

R: El backend Django hace un `POST` HTTP al servidor FastAPI con el frame codificado en base64 o como archivo. El servidor FastAPI devuelve un JSON con las detecciones. Todo ocurre en la red local.

```
Django (puerto 8000) → HTTP POST → FastAPI (puerto 8001)
                     ← JSON respuesta ←
```

---

**P: Si un compañero quiere entrenar un modelo para vehículos mal estacionados, ¿qué tiene que hacer?**

R:
1. Recolectar imágenes/videos de autos mal estacionados y bien estacionados en el condominio.
2. Organizar en carpetas: `train/mal_estacionado/`, `train/bien_estacionado/`, `val/...`
3. Adaptar `entrenamiento_condominio.ipynb` cambiando el dataset y el número de clases.
4. Partir de `modelo_condominio_final.pt` como base (ya sabe qué son vehículos en nuestro condominio).
5. Reemplazar `fc = nn.Linear(512, 2)` (2 clases: mal/bien estacionado).
6. Guardar como `modelo_vehiculo_acciones.pth` y subir al repo.
7. Crear `vehiculo_accion_classifier.py` copiando la estructura de `pelea_classifier.py`.

---

*Documento generado para el proyecto SIVIC — Defensa final Software I 2026*
