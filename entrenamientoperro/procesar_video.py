# procesar_video.py
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from app.classifier.resnet_classifier import ResNetClassifier
from app.detectors.poop_detector import PoopDetector

# Configuración de rutas
VIDEO_PATH = r"C:\Users\HP\Downloads\p2.mp4"
OUTPUT_DIR = Path("outputs")
OUTPUT_VIDEO_PATH = OUTPUT_DIR / "resultado_p2.mp4"

# Cargar modelos
print("Cargando modelos para el procesamiento de video...")
yolo_model = YOLO("yolov8n.pt")

# Cargar el clasificador ResNet50 para razas
model_path = Path(r"D:\SW1\entrenamientoperro\models\resnet50_dogs.pth")
classes_path = Path(r"D:\SW1\entrenamientoperro\models\classes.json")
resnet_classifier = None
if model_path.exists() and classes_path.exists():
    try:
        resnet_classifier = ResNetClassifier(
            model_path=str(model_path),
            classes_path=str(classes_path)
        )
        print("Clasificador de razas (ResNet50) cargado con exito.")
    except Exception as e:
        print(f"No se pudo cargar el clasificador de razas: {e}")
else:
    print("Advertencia: No se encontraron los archivos de ResNet50. Se omitira la clasificacion de raza.")

# Cargar el detector de heces
poop_detector = PoopDetector()
print("Modelos listos.")

def main():
    if not Path(VIDEO_PATH).exists():
        print(f"Error: El video de entrada no existe en {VIDEO_PATH}")
        return

    # Abrir video
    cap = cv2.VideoCapture(VIDEO_PATH)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Procesando video: {VIDEO_PATH}")
    print(f"Resolucion: {width}x{height} | FPS: {fps:.2f} | Total Frames: {total_frames}")

    # Crear carpeta de salida
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Configurar VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT_VIDEO_PATH), fourcc, fps, (width, height))

    frame_count = 0
    
    # Umbral de distancia para perro suelto (25% del ancho del video)
    umbral_distancia = width * 0.25

    # Para evitar clasificar la raza en cada cuadro (que es muy lento),
    # guardaremos la raza identificada por ID de perro en un diccionario.
    razas_por_id = {}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % 30 == 0 or frame_count == 1:
            print(f"Procesando frame {frame_count}/{total_frames}...")

        # 1. Ejecutar YOLOv8 con tracking
        # Usamos persist=True para mantener los IDs de los objetos a lo largo del video
        results = yolo_model.track(frame, persist=True, verbose=False)
        
        bboxes_perros = []
        bboxes_personas = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                clase_id = int(box.cls[0])
                # Para evitar fallos si el tracker no asigna ID en los primeros frames, usamos un ID por defecto
                track_id = int(box.id[0]) if box.id is not None else -1
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                
                if clase_id == 16:  # dog
                    bboxes_perros.append({
                        "bbox": [x1, y1, x2, y2],
                        "id": track_id,
                        "confianza": conf
                    })
                elif clase_id == 0:  # person
                    bboxes_personas.append({
                        "bbox": [x1, y1, x2, y2],
                        "id": track_id,
                        "confianza": conf
                    })

        # 2. Dibujar personas
        for persona in bboxes_personas:
            x1, y1, x2, y2 = persona["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, f"Persona #{persona['id']}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # 3. Evaluar proximidad y dibujar perros
        for perro in bboxes_perros:
            px1, py1, px2, py2 = perro["bbox"]
            pid = perro["id"]
            
            px_c = (px1 + px2) / 2
            py_c = (py1 + py2) / 2
            
            # Clasificar raza si es un nuevo ID de perro
            if resnet_classifier and pid not in razas_por_id and pid != -1:
                crop = frame[max(0, py1):min(height, py2), max(0, px1):min(width, px2)]
                if crop.size > 0:
                    try:
                        raza_pred = resnet_classifier.predict(crop)
                        razas_por_id[pid] = raza_pred.title()
                    except Exception:
                        razas_por_id[pid] = "Perro"
            
            raza_label = razas_por_id.get(pid, "Perro")

            # Buscar persona mas cercana
            distancia_minima = float('inf')
            persona_cercana = None
            
            for persona in bboxes_personas:
                hx1, hy1, hx2, hy2 = persona["bbox"]
                hx_c = (hx1 + hx2) / 2
                hy_c = (hy1 + hy2) / 2
                
                dist = np.sqrt((px_c - hx_c)**2 + (py_c - hy_c)**2)
                if dist < distancia_minima:
                    distancia_minima = dist
                    persona_cercana = (int(hx_c), int(hy_c))

            # Verificar si esta sin correa (suelto)
            esta_suelto = distancia_minima > umbral_distancia
            
            if esta_suelto:
                # Alerta: perro suelto (Color rojo)
                cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 3)
                cv2.putText(frame, f"ALERTA: {raza_label} #{pid} SUELTO", (px1, py1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                # Imprimir en consola de forma visible
                print(f"[ALERTA] Frame {frame_count}: {raza_label} #{pid} esta SUELTO (Distancia a humano: {distancia_minima:.1f}px)")
            else:
                # Acompañado (Color verde)
                cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 0), 2)
                cv2.putText(frame, f"{raza_label} #{pid} (Con dueño)", (px1, py1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                # Dibujar linea de conexion
                if persona_cercana:
                    cv2.line(frame, (int(px_c), int(py_c)), persona_cercana, (0, 255, 255), 2)
                print(f"[INFO] Frame {frame_count}: {raza_label} #{pid} esta acompañado por dueño (Distancia: {distancia_minima:.1f}px)")

        # 4. Detectar heces (ejecutado cada 5 frames para agilizar la inferencia)
        if frame_count % 5 == 0:
            heces = poop_detector.detect(frame)
            # Dibujar heces
            for h in heces:
                # Si el poop_detector no es simulado o si detecta heces reales
                hx1, hy1, hx2, hy2 = h["bbox"]
                conf = h["confianza"]
                clase = h.get("clase", "Heces")
                cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (0, 165, 255), 2)
                cv2.putText(frame, f"ALERTA: {clase} ({conf:.2f})", (hx1, hy1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                print(f"[ALERTA HECES] Frame {frame_count}: {clase} detectada con confianza {conf:.2f}")

        # Escribir frame en el video de salida
        out.write(frame)

    cap.release()
    out.release()
    print(f"\nProcesamiento terminado con exito.")
    print(f"Video guardado en: {OUTPUT_VIDEO_PATH.resolve()}")

if __name__ == "__main__":
    main()
