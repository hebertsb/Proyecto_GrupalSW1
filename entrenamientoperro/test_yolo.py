# test_yolo.py - Prueba simple de YOLO
from ultralytics import YOLO
import cv2
from pathlib import Path

# Cargar modelo
model = YOLO('yolov8n.pt')

# Usar una imagen de prueba (si no tienes, descarga una de internet)
# O usa cualquier imagen que tengas con perros
imagen_path = "test_dog.jpg"  # Cambia por tu imagen

if not Path(imagen_path).exists():
    # Intentar usar una imagen real del dataset de Stanford Dogs como fallback
    fallback_path = Path(r"D:\SW1\entrenamientoperro\data\raw\stanford_dogs\Images\n02085620-Chihuahua\n02085620_10074.jpg")
    if fallback_path.exists():
        imagen_path = str(fallback_path)
    else:
        print(f"❌ No encuentro {imagen_path} ni el fallback en {fallback_path}")
        print("Descarga una imagen de perro de internet o usa otra ruta")
        exit()

# Detectar
results = model(imagen_path)

# Crear carpeta de salida
Path("outputs").mkdir(exist_ok=True)

# Procesar resultados
perros = []
for r in results:
    for box in r.boxes:
        clase_id = int(box.cls[0])
        if clase_id == 16:  # dog en COCO
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            perros.append((x1, y1, x2, y2, conf))
            print(f"✅ Perro detectado: [{x1},{y1},{x2},{y2}] confianza: {conf:.2f}")

# Dibujar y guardar
img = cv2.imread(imagen_path)
for x1, y1, x2, y2, conf in perros:
    cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
    cv2.putText(img, f"Perro {conf:.2f}", (x1, y1-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

output_path = "outputs/resultado.jpg"
cv2.imwrite(output_path, img)
print(f"📁 Imagen guardada en: {output_path}")
print(f"📊 Total perros detectados: {len(perros)}")