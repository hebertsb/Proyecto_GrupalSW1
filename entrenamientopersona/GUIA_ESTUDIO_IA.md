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
8. [Los 3 servidores IA del sistema](#8-los-3-servidores-ia-del-sistema)
9. [Detección en producción — flujo completo](#9-detección-en-producción--flujo-completo)
10. [Detección de personas con YOLO](#10-detección-de-personas-con-yolo)
11. [Por qué se usan DOS modelos distintos para personas](#11-por-qué-se-usan-dos-modelos-distintos-para-personas)
12. [El endpoint /analizar — las 8 alertas](#12-el-endpoint-analizar--las-8-alertas)
13. [Las reglas del sistema](#13-las-reglas-del-sistema)
14. [Conteo y clasificación de nivel](#14-conteo-y-clasificación-de-nivel)
15. [Cómo Django llama al servidor IA](#15-cómo-django-llama-al-servidor-ia)
16. [¿Dónde está cada archivo?](#16-dónde-está-cada-archivo)
17. [Preguntas frecuentes de defensa](#17-preguntas-frecuentes-de-defensa)

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

## 8. Los 3 servidores IA del sistema

El sistema SIVIC tiene **3 servidores FastAPI independientes**, uno por área de detección. Todos se ejecutan con el mismo comando `uvicorn api:app` pero en puertos distintos.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Servidor 1 — Personas y Vehículos                                  │
│  Carpeta: entrenamientopersona/                                     │
│  Comando: python -m uvicorn api:app --host 0.0.0.0 --port 8002     │
│                                                                     │
│  Modelos que usa:                                                   │
│    ┌─ modelo_condominio_final.pt ─ YOLOv8 fine-tuned personas       │
│    ├─ yolov8n.pt (fallback)     ─ YOLO base si no hay .pt          │
│    ├─ modelo_pelea.pth          ─ ResNet18 Fight/NonFight           │
│    └─ modelo_vehiculo_estacionamiento.pth ─ ResNet18 mal/bien       │
│                                                                     │
│  Alertas que genera:                                                │
│    zona_restringida_persona, merodeo, personas_peleando,            │
│    caida_persona, intrusion_nocturna, acceso_fuera_horario,         │
│    vehiculo_zona_restringida, vehiculo_mal_estacionado              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Servidor 2 — Perros y Heces                                        │
│  Carpeta: entrenamientoperro/                                       │
│  Comando: python -m uvicorn api:app --host 0.0.0.0 --port 8002     │
│                                                                     │
│  Modelos que usa:                                                   │
│    ┌─ yolov8n.pt              ─ YOLO base, clase 16 = perro        │
│    ├─ models/resnet50_dogs.pth ─ ResNet50 clasificador de raza      │
│    └─ PoopDetector            ─ detector de heces en suelo          │
│                                                                     │
│  Alertas que genera:                                                │
│    sin_correa (perro lejos de persona), heces_no_limpiadas          │
│                                                                     │
│  Variables de entorno necesarias:                                   │
│    DOGS_RESNET_PATH=models/resnet50_dogs.pth                        │
│    DOGS_CLASSES_PATH=models/classes.json                            │
│    DOGS_IMAGES_DIR=data/raw/stanford_dogs/Images                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Servidor 3 — Vehículos personalizados (en desarrollo)             │
│  Sigue la misma estructura que el Servidor 1                        │
│  Punto de entrada: api.py con app = FastAPI(...)                    │
│  Endpoint mínimo requerido: POST /analizar                          │
└─────────────────────────────────────────────────────────────────────┘
```

### ¿Cómo Django sabe qué servidor IA usar para cada cámara?

Cada cámara en la base de datos tiene configurado `ia_url` — la URL del servidor FastAPI que debe consultar. Django llama a ese URL al recibir frames:

```python
# En Django: camaras/views.py
ia_url = camara.ia_url  # ej: "http://127.0.0.1:8002"
resp = req_ext.post(f"{ia_url}/api/analizar", files=..., timeout=10)
```

Esto permite que cámara A use el servidor de personas y cámara B use el de perros, sin modificar código — solo configurando `ia_url` en la base de datos.

---

## 9. Detección en producción — flujo completo

```
Cámara IP / RTSP / MJPEG / Cámara Local (Android)
          │
          ▼
┌──────────────────────────────────┐
│  Django: camaras/views.py        │
│  stream_mjpeg_async()            │
│  → captura frames del stream     │
│  → cada 2 segundos llama a       │
│    analizar_ia()                 │
└──────────────┬───────────────────┘
               │  POST /api/analizar (frame JPEG + camara_id + zonas_json)
               ▼
┌──────────────────────────────────────────────────┐
│  FastAPI — entrenamientopersona/api.py           │
│  endpoint: POST /analizar                        │
│                                                  │
│  1. PersonaDetector.detect(frame)                │
│     → usa modelo_condominio_final.pt             │
│     → devuelve lista de bboxes de personas       │
│                                                  │
│  2. VehiculoDetector.detect(frame)               │
│     → usa yolov8n.pt clases 2,3,5,7             │
│     → devuelve bboxes de autos/motos/bus/camión  │
│                                                  │
│  3. Reglas sobre personas (6 reglas)             │
│  4. PeleaClassifier.clasificar(frame)            │
│     → ResNet18 modelo_pelea.pth                  │
│     → dice si hay pelea con confianza %          │
│                                                  │
│  5. Reglas sobre vehículos (2 reglas)            │
│  6. VehiculoEstacionamientoClassifier.clasificar │
│     → ResNet18 modelo_vehiculo_estacionamiento   │
│                                                  │
│  Respuesta JSON: {                               │
│    alertas: ["merodeo", "personas_peleando"],    │
│    detecciones: [{clase, confianza, bbox},...],  │
│    conteo: {personas: 3, vehiculos: 1}           │
│  }                                               │
└──────────────────────┬───────────────────────────┘
                       │ JSON de vuelta a Django
                       ▼
┌──────────────────────────────────────────────────┐
│  Django: analizar_ia() continúa                  │
│                                                  │
│  → cuenta personas detectadas                    │
│  → calcula nivel: normal/sospechoso/crítico      │
│  → si hay alertas → crea Evento en base de datos │
│  → emite WebSocket a clientes conectados         │
│  → Angular y Flutter reciben la alerta en tiempo │
│    real sin necesidad de refrescar               │
└──────────────────────┬───────────────────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
  ┌─────────────────┐   ┌──────────────────┐
  │  Angular Web    │   │  Flutter App     │
  │  Badge campana  │   │  Push + alerta   │
  │  Panel NVR      │   │  en pantalla     │
  └─────────────────┘   └──────────────────┘
```

---

## 10. Detección de personas con YOLO

Para detectar personas y vehículos usamos un modelo diferente: **YOLOv8n** (You Only Look Once, versión 8, nano).

A diferencia de ResNet18 que clasifica toda la imagen, YOLO **localiza objetos** dentro de la imagen dibujando bounding boxes.

**Archivo:** `entrenamientopersona/app/detectors/persona_detector.py`

```python
from ultralytics import YOLO

class PersonaDetector:
    CLASE_ID = 0  # 'person' en COCO

    def __init__(self, model_path=None):
        import os
        if model_path is None:
            # Primero intenta usar el modelo fine-tuned del condominio
            model_path = os.getenv("PERSONA_MODEL_PATH", "modelo_condominio_final.pt")
            if not Path(model_path).exists():
                model_path = "yolov8n.pt"   # fallback al base si no encuentra el .pt
        self.model = YOLO(model_path)

    def detect(self, img, conf_min=0.35):
        results = self.model(img, verbose=False)
        personas = []
        for r in results:
            for box in r.boxes:
                if int(box.cls[0]) != self.CLASE_ID:
                    continue
                conf = float(box.conf[0])
                if conf < conf_min:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                personas.append({"bbox": [x1, y1, x2, y2], "confianza": round(conf, 3)})
        return personas
```

**Importante:** `yolov8n.pt` es el modelo oficial de Ultralytics, entrenado en el dataset COCO (80 categorías de objetos comunes). La clase 0 en COCO siempre es "person". Las clases de vehículos son 2=auto, 3=moto, 5=bus, 7=camión.

### YOLO vs ResNet18

| | YOLO | ResNet18 |
|---|---|---|
| Tarea | Detección (dónde está) | Clasificación (qué es) |
| Salida | Bounding boxes + clases | Una clase para toda la imagen |
| Uso en SIVIC | Detectar y contar personas | Clasificar si hay pelea |
| Modelo | modelo_condominio_final.pt | modelo_pelea.pth (nuestro) |

---

## 11. Por qué se usan DOS modelos distintos para personas

Esta es la pregunta más importante para la defensa sobre el modelo.

### `yolov8n.pt` — modelo base COCO

- Entrenado por Ultralytics con 80 categorías genéricas (perros, autos, personas, etc.)
- Detecta personas en cualquier contexto (estadio, calle, supermercado)
- **Tarea:** encontrar dónde están las personas (bounding boxes)
- Clase 0 del dataset COCO = persona

### `modelo_condominio_final.pt` — modelo fine-tuned (el que entrenamos)

- Partió del mismo YOLO base pero fue re-entrenado con **imágenes específicas del condominio**
- Conoce los ángulos de cámara, las condiciones de luz, el tipo de personas en zonas del condominio
- **Resultado:** más preciso en nuestro ambiente específico, menos falsos positivos
- **Tarea:** también detectar personas (bounding boxes), pero optimizado para nuestras cámaras

### El bug que existía antes

```python
# ANTES — el código ignoraba el modelo entrenado
def __init__(self, model_path: str = "yolov8n.pt"):   # hardcoded al genérico
    self.model = YOLO(model_path)
```

```python
# AHORA — usa el modelo fine-tuned, con fallback si no existe el archivo
def __init__(self, model_path=None):
    model_path = os.getenv("PERSONA_MODEL_PATH", "modelo_condominio_final.pt")
    if not Path(model_path).exists():
        model_path = "yolov8n.pt"   # respaldo automático
    self.model = YOLO(model_path)
```

**Analogía:** sería como tener un médico especializado en pediatría y uno general. Para atender niños, el especialista da mejores resultados. Antes estábamos usando siempre al médico general aunque teníamos al especialista disponible.

---

## 12. El endpoint /analizar — las 8 alertas

El endpoint `POST /analizar` de `entrenamientopersona/api.py` es el corazón del sistema. Recibe un frame y devuelve hasta 8 tipos de alerta.

```python
@router.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    camara_id:      int           = Form(DEFAULT_CAMARA_ID),
    zonas_json:     Optional[str] = Form(None),   # zonas prohibidas del plano
    umbral_merodeo: int           = Form(30),      # segundos para considerar merodeo
):
```

### Las 8 alertas posibles

| # | Nombre alerta | Qué la dispara | Modelo/regla |
|---|---|---|---|
| 1 | `zona_restringida_persona` | Persona detectada dentro de zona prohibida | YOLO + geometría polígono |
| 2 | `merodeo` | Persona en misma zona >N segundos | YOLO + historial en RAM |
| 3 | `personas_peleando` | ≥2 personas y clasificador dice "Fight" ≥75% | ResNet18 `modelo_pelea.pth` |
| 4 | `caida_persona` | bbox de persona más ancho que alto (ratio > 1.4) | YOLO + geometría bbox |
| 5 | `intrusion_nocturna` | Persona detectada entre 22:00 y 06:00 | YOLO + hora del sistema |
| 6 | `acceso_fuera_horario` | Persona en zona `horario_restringido` fuera del horario | YOLO + zona + hora |
| 7 | `vehiculo_zona_restringida` | Vehículo dentro de zona prohibida | YOLO + geometría polígono |
| 8 | `vehiculo_mal_estacionado` | Clasificador dice "infraccion" ≥75% | ResNet18 `modelo_vehiculo_estacionamiento.pth` |

### Respuesta JSON del endpoint

```json
{
  "alertas": ["merodeo", "personas_peleando"],
  "detalle_alertas": [
    {"tipo": "merodeo", "segundos": 45.2, "bbox": [120, 80, 300, 450], "confianza": 0.87},
    {"tipo": "personas_peleando", "confianza": 0.91}
  ],
  "detecciones": [
    {"clase": "persona", "confianza": 0.89, "bbox": {"x": 0.18, "y": 0.16, "w": 0.28, "h": 0.77}},
    {"clase": "vehiculo", "confianza": 0.76, "tipo_vehiculo": "auto", "bbox": {...}}
  ],
  "conteo": {"personas": 2, "vehiculos": 1}
}
```

Las coordenadas del bbox están **normalizadas de 0 a 1** (relativas al tamaño de la imagen). Esto permite que Angular/Flutter las muestre correctamente sin importar la resolución de la cámara.

---

## 13. Las reglas del sistema

Las reglas son lógica adicional que se aplica **sobre las detecciones de YOLO**, sin modelos de ML adicionales.

### Regla 1: Zona Restringida — `reglas/zona_restringida.py`

```python
def verificar_zonas(detecciones, zonas, alto, ancho):
    for det in detecciones:
        x1, y1, x2, y2 = det["bbox"]
        cx = (x1 + x2) / 2
        cy = float(y2)          # pie de la persona (punto inferior del bbox)
        for zona in zonas:
            puntos = zona["puntos"]
            if zona.get("normalizado"):
                puntos = [[p[0]*ancho, p[1]*alto] for p in puntos]
            # Prueba si el pie está dentro del polígono de la zona
            if cv2.pointPolygonTest(np.array(puntos), (cx, cy), False) >= 0:
                violaciones.append(...)
```

Las zonas vienen del plano del condominio en Angular: el guardia dibuja el polígono de la zona prohibida y se envían junto con cada frame.

### Regla 2: Merodeo — `reglas/merodeo.py`

```python
_historial = defaultdict(list)   # en RAM, por camara_id
_DIST_PX   = 120                 # radio para considerar "misma zona"
_MAX_SEG   = 300                 # borra historial de más de 5 min

def verificar_merodeo(detecciones, camara_id, umbral_seg=30):
    # Para cada persona detectada:
    # 1. Calcula el centro del bbox
    # 2. Busca en el historial puntos cercanos (radio 120px)
    # 3. Si los hay y llevan más de umbral_seg segundos → alerta
```

**Limitación:** el historial vive en RAM. Si el servidor FastAPI se reinicia, se pierde. Para producción habría que persistir en Redis o base de datos.

### Regla 3: Caída — `reglas/caida.py`

```python
_RATIO_CAIDA = 1.4  # si ancho/alto > 1.4 → persona horizontal = posible caída

def verificar_caida(detecciones):
    for d in detecciones:
        x1, y1, x2, y2 = d["bbox"]
        ancho = x2 - x1
        alto  = y2 - y1
        if alto > 0 and (ancho / alto) >= _RATIO_CAIDA:
            # El bbox es más ancho que alto → persona acostada
            alertas.append(...)
```

Lógica simple pero efectiva: una persona de pie tiene bbox más alto que ancho. Una persona caída tiene bbox más ancho que alto.

### Regla 4: Intrusión Nocturna — `reglas/horario.py`

```python
def verificar_intrusion_nocturna(detecciones,
    hora_inicio=dtime(22, 0),   # 22:00
    hora_fin=dtime(6, 0)):      # 06:00
    # El rango cruza medianoche
    if hora_inicio > hora_fin:
        es_nocturno = ahora >= hora_inicio or ahora <= hora_fin
```

### Regla 5: Acceso Fuera de Horario — `reglas/horario.py`

```python
def verificar_acceso_fuera_horario(detecciones, zonas,
    hora_permitida_inicio=dtime(8, 0),   # horario laboral
    hora_permitida_fin=dtime(14, 0)):
    # Busca zonas con nombre "horario_restringido"
    # Si hay personas en esas zonas y estamos fuera del horario → alerta
```

---

## 14. Conteo y clasificación de nivel

Una vez que YOLO detecta las personas en el frame, el backend Django cuenta cuántas hay y asigna un nivel de alerta.

**Archivo:** `apps/sivic_backend/camaras/views.py`

```python
# Filtra solo las detecciones de personas (no vehículos)
_personas_det = [
    d for d in resultado.get('detecciones', [])
    if d.get('clase') in ('persona', 'person')
]

# Cuenta cuántas personas hay
_conteo_personas = len(_personas_det)

# Asigna nivel según cantidad
if _conteo_personas >= 6:
    _nivel = 'critico'       # 6 o más personas → CRÍTICO (rojo parpadeante)
elif _conteo_personas >= 3:
    _nivel = 'sospechoso'    # 3 a 5 personas → SOSPECHOSO (amarillo)
else:
    _nivel = 'normal'        # 0 a 2 personas → NORMAL (verde)
```

Estos valores se muestran en el panel web (Angular) con un badge de color sobre cada celda de cámara:

```
0-2 personas → badge verde   "2 · NORMAL"
3-5 personas → badge amarillo "4 · SOSPECHOSO"
6+  personas → badge rojo parpadeante "7 · CRÍTICO"
```

---

## 15. Cómo Django llama al servidor IA

**Archivo:** `apps/sivic_backend/camaras/views.py` → función `analizar_ia()`

```python
@api_view(["POST"])
def analizar_ia(request, pk):
    camara = get_object_or_404(Camara, pk=pk)

    # 1. Leer el frame del request (imagen JPEG enviada por el cliente)
    imagen_bytes = request.data.get('imagen')

    # 2. Preparar las zonas prohibidas (del plano del condominio)
    zonas = list(camara.posicionplano_set
                 .filter(plano__activo=True)
                 .values('nombre', 'puntos', 'normalizado'))

    # 3. Llamar al servidor FastAPI con el frame
    ia_url = camara.ia_url   # configurado en la BD por cámara, ej: "http://127.0.0.1:8002"
    resp = req_ext.post(
        f"{ia_url}/api/analizar",
        files={"file": ("frame.jpg", imagen_bytes, "image/jpeg")},
        data={
            "camara_id": camara.pk,
            "umbral_merodeo": 90,          # 90 segundos para merodeo
            "zonas_json": json.dumps(zonas),
        },
        timeout=10,
    )

    resultado = resp.json()

    # 4. Procesar resultado: contar personas, calcular nivel
    _personas_det = [d for d in resultado.get('detecciones', [])
                     if d.get('clase') in ('persona', 'person')]
    _nivel = 'critico' if len(_personas_det) >= 6 else \
             'sospechoso' if len(_personas_det) >= 3 else 'normal'

    resultado['conteo_personas'] = len(_personas_det)
    resultado['nivel'] = _nivel

    # 5. Si hay alertas → crear Evento en base de datos
    for alerta in resultado.get('alertas', []):
        # Busca la regla correspondiente y crea el evento
        ...

    # 6. Emitir WebSocket a todos los clientes conectados
    channel_layer.group_send("camaras", {
        "type": "camara_update",
        "data": resultado,
    })

    return Response(resultado)
```

### El ciclo completo en tiempo real

```
Angular/Flutter                Django                    FastAPI
     │                            │                          │
     │─── POST frame JPEG ───────►│                          │
     │                            │─── POST /api/analizar ──►│
     │                            │                          │ detecta
     │                            │◄── JSON resultado ───────│
     │                            │ cuenta, asigna nivel     │
     │                            │ crea Evento en BD        │
     │◄── WebSocket "alerta" ─────│                          │
     │ muestra badge/notificación  │                          │
```

---

## 16. ¿Dónde está cada archivo?

```
SmartCondominium/
│
├── entrenamientopersona/                    ← Servidor IA principal (FastAPI)
│   │
│   ├── modelo_condominio_final.pt           ← Modelo fine-tuned YOLO para personas
│   │                                           Entrenado con imágenes del condominio
│   │                                           Usado por PersonaDetector en producción
│   │
│   ├── modelo_pelea.pth                     ← Modelo Fight/NonFight
│   │                                           ResNet18, 20,000 frames de videos
│   │                                           Umbral: 75% de confianza
│   │
│   ├── modelo_vehiculo_estacionamiento.pth  ← Modelo mal/bien estacionado
│   │                                           ResNet18, clases: infraccion/normal
│   │
│   ├── yolov8n.pt                           ← Modelo YOLO base COCO (fallback)
│   │                                           Usado si no existe .pt fine-tuned
│   │
│   ├── api.py                               ← FastAPI: endpoint POST /analizar
│   │                                           8 tipos de alertas, 2 detectores
│   │
│   ├── app/detectors/
│   │   ├── persona_detector.py              ← YOLO clase 0, usa modelo_condominio_final.pt
│   │   └── vehiculo_detector.py             ← YOLO clases 2,3,5,7 (auto,moto,bus,camión)
│   │
│   ├── app/classifiers/
│   │   ├── pelea_classifier.py              ← ResNet18 modelo_pelea.pth, umbral 0.75
│   │   └── vehiculo_estacionamiento_classifier.py ← ResNet18, umbral 0.75
│   │
│   └── reglas/
│       ├── zona_restringida.py              ← Geometría de polígono (cv2.pointPolygonTest)
│       ├── merodeo.py                       ← Historial en RAM por camara_id
│       ├── caida.py                         ← Ratio bbox ancho/alto > 1.4
│       └── horario.py                       ← Verificación de hora del sistema
│
├── entrenamientoperro/                      ← Servidor IA perros (FastAPI)
│   ├── api.py                               ← POST /analizar: detecta perros+heces
│   ├── app/detectors/poop_detector.py       ← Detector de heces en suelo
│   └── app/classifier/resnet_classifier.py  ← ResNet50 clasificador de raza
│
└── apps/sivic_backend/                      ← Backend principal (Django)
    └── camaras/
        └── views.py                         ← analizar_ia(): llama al FastAPI,
                                                cuenta personas, asigna nivel,
                                                crea Evento, emite WebSocket
```

### Variables de entorno por servidor

Cada servidor IA necesita un `.env` en su carpeta:

```env
# entrenamientopersona/.env
DJANGO_BACKEND_URL=http://127.0.0.1:8000
DEFAULT_CAMARA_ID=9
PERSONA_MODEL_PATH=modelo_condominio_final.pt
PELEA_MODEL_PATH=modelo_pelea.pth
VEHICULO_EST_MODEL_PATH=modelo_vehiculo_estacionamiento.pth

# entrenamientoperro/.env
DJANGO_BACKEND_URL=http://127.0.0.1:8000
DEFAULT_CAMARA_ID=9
DOGS_RESNET_PATH=models/resnet50_dogs.pth
DOGS_CLASSES_PATH=models/classes.json
DOGS_IMAGES_DIR=data/raw/stanford_dogs/Images
```

---

## 17. Preguntas frecuentes de defensa

**P: ¿Por qué usaron ResNet18 y no una red más grande como ResNet50 o VGG?**

R: ResNet18 es un buen equilibrio entre precisión y velocidad. Para clasificación binaria (pelea/no pelea) con 20,000 imágenes, una red más grande no mejora significativamente la precisión pero es más lenta para inferencia en tiempo real. Necesitamos procesar frames cada 2 segundos por cámara.

---

**P: ¿Por qué YOLO para personas y ResNet18 para peleas? ¿No podrían hacer todo con un solo modelo?**

R: Son tareas distintas:
- YOLO hace **detección** (encuentra dónde están los objetos en la imagen, múltiples objetos simultáneamente).
- ResNet18 hace **clasificación** (decide qué sucede en toda la imagen).
Para contar cuántas personas hay necesitamos YOLO (bounding boxes individuales). Para detectar peleas, basta con clasificar la escena completa.

---

**P: ¿Qué es `modelo_condominio_final.pt` y por qué tienen ese archivo si ya tienen `yolov8n.pt`?**

R: `yolov8n.pt` es el modelo genérico de Ultralytics, entrenado en 80 categorías del dataset COCO. `modelo_condominio_final.pt` es el mismo modelo pero **re-entrenado (fine-tuned) con 9,489 imágenes específicas de nuestro condominio**: los ángulos de las cámaras del lugar, las condiciones de luz, los tipos de personas que circulan. El fine-tuned es más preciso en nuestro ambiente específico. Por eso ahora se usa como primera opción, con el genérico como respaldo si el archivo no existe.

---

**P: ¿Qué tan preciso es el modelo de peleas?**

R: El dataset Kaggle real-life-violence-situations-dataset tiene un balance perfecto (1000 Fight / 1000 NonFight). Con fine-tuning de ResNet18, los modelos similares en literatura alcanzan ~90-95% de precisión en validación. Usamos un umbral de 0.75 (75% de confianza mínima) para reducir falsos positivos.

---

**P: ¿El sistema analiza video en tiempo real o fotos aisladas?**

R: Analiza frames individuales (fotografías), no video continuo. El backend llama al servidor IA cada 2 segundos con un frame capturado de la cámara. La detección temporal (¿lleva tiempo ahí?) la maneja el sistema de reglas del backend — ejemplo: merodeo = misma persona detectada en la misma zona durante más de 90 segundos.

---

**P: ¿Cómo se comunica el servidor IA (Python/FastAPI) con el backend (Django)?**

R: Django recibe los frames de las cámaras (RTSP, MJPEG o Android). Cuando el sistema está en modo análisis, Django hace un `POST` HTTP al servidor FastAPI con el frame como archivo. FastAPI devuelve un JSON con las detecciones y alertas. Django procesa el resultado, crea eventos en la base de datos y emite WebSocket a los clientes.

```
Django (puerto 8000) → HTTP POST → FastAPI (puerto 8002)
                     ← JSON respuesta ←
Django → WebSocket → Angular/Flutter (tiempo real)
```

---

**P: ¿Qué pasa si el servidor FastAPI se cae?**

R: Django captura el error del `requests.post()` con `try/except` y devuelve un error controlado. No rompe el sistema principal. El stream de video sigue funcionando, solo se deja de analizar IA hasta que el servidor IA vuelva a estar disponible.

---

**P: Si un compañero quiere agregar un modelo nuevo (ej: reconocimiento de placas), ¿qué tiene que hacer?**

R:
1. Entrenar el modelo (puede partir de `modelo_condominio_final.pt` como base).
2. Crear `app/classifiers/placa_classifier.py` copiando la estructura de `pelea_classifier.py`.
3. En `api.py`: importar el clasificador, cargarlo en `startup()`, llamarlo en `/analizar`.
4. Agregar la alerta nueva (`"placa_no_registrada"`) a la lista de alertas del response.
5. En Django: agregar la regla correspondiente en la base de datos.
6. Angular/Flutter: el nuevo tipo de alerta aparece automáticamente en el panel de eventos.

---

*Documento SIVIC — Sistema de Visión Inteligente para Condominios — Software I 2026*
