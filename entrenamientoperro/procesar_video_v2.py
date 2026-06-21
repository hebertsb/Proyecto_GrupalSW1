import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from app.classifier.resnet_classifier import ResNetClassifier
from app.detectors.poop_detector import PoopDetector

# Configuración de rutas
VIDEO_PATH = r"C:\Users\HP\Downloads\p2.mp4"
OUTPUT_DIR = Path("outputs")
OUTPUT_VIDEO_PATH = OUTPUT_DIR / "resultado_inteligente.mp4"

# Cargar modelos
print("Cargando el equipo de IA...")
modelo_personas = YOLO("yolov8n.pt") # Solo para dibujar humanos

# AQUÍ VA EL MODELO QUE SE ESTÁ ENTRENANDO AHORITA EN TU TERMINAL (correa)
modelo_correa = YOLO(r"runs\detect\detector_correa-3\weights\best.pt")

# Tu clasificador de razas
model_path = Path(r"D:\SW1\entrenamientoperro\models\resnet50_dogs.pth")
classes_path = Path(r"D:\SW1\entrenamientoperro\models\classes.json")
resnet_classifier = None
if model_path.exists() and classes_path.exists():
    try:
        resnet_classifier = ResNetClassifier(str(model_path), str(classes_path))
        print("✅ Clasificador de razas (ResNet50) cargado con exito.")
    except Exception as e:
        print(f"⚠️ No se pudo cargar el clasificador de razas: {e}")

# Detector de heces (¡Usará automáticamente el feces_yolo.pt experto de Colab que descargaste!)
poop_detector = PoopDetector()
print("✅ Todos los modelos listos.")

def main():
    if not Path(VIDEO_PATH).exists():
        print(f"Error: El video de entrada no existe en {VIDEO_PATH}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT_VIDEO_PATH), fourcc, fps, (width, height))

    frame_count = 0
    razas_por_id = {}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        frame_count += 1
        eventos_del_frame = []
        
        # Opcional: imprimir el número de frame para ver avance sin saturar
        if frame_count % 30 == 0:
            print(f"--- Procesando Frame {frame_count}/{total_frames} ---")

        # 1. PERSONAS: Usamos el YOLO base solo para detectar personas (clase 0)
        resultados_personas = modelo_personas.predict(frame, classes=[0], verbose=False)
        for box in resultados_personas[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, "Persona", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            eventos_del_frame.append(f"🧑 Humano Detectado (Conf: {float(box.conf[0]):.2f})")

        # 2. PERROS Y CORREAS: Usamos el NUEVO modelo de la correa con tracking
        resultados_correa = modelo_correa.track(frame, persist=True, verbose=False)
        
        if resultados_correa and resultados_correa[0].boxes is not None:
            for box in resultados_correa[0].boxes:
                # Obtenemos nombre de la clase (Dog-with-Leash o Dog-without-Leash)
                clase_idx = int(box.cls[0])
                nombre_clase = modelo_correa.names[clase_idx] 
                track_id = int(box.id[0]) if box.id is not None else -1
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                # Clasificar raza si es un perro nuevo
                if resnet_classifier and track_id not in razas_por_id and track_id != -1:
                    crop = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
                    if crop.size > 0:
                        try:
                            raza_pred = resnet_classifier.predict(crop)
                            razas_por_id[track_id] = raza_pred.title()
                        except:
                            razas_por_id[track_id] = "Perro"
                
                raza_label = razas_por_id.get(track_id, "Perro")

                # Analizar la etiqueta de la correa
                if nombre_clase == "Dog-without-Leash":
                    color = (0, 0, 255) # Rojo ALERTA
                    texto = f"ALERTA SUELTO: {raza_label} #{track_id}"
                    eventos_del_frame.append(f"❌ PERRO SUELTO [{raza_label} #{track_id}] (Conf: {float(box.conf[0]):.2f})")
                else:
                    color = (0, 255, 0) # Verde SEGURO
                    texto = f"SEGURO: {raza_label} #{track_id}"
                    eventos_del_frame.append(f"✅ Perro con Correa [{raza_label} #{track_id}]")

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, texto, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 3. DETECTAR HECES Y POSTURA (Ejecutado cada 5 frames)
        if frame_count % 5 == 0:
            heces = poop_detector.detect(frame)
            for h in heces:
                hx1, hy1, hx2, hy2 = h["bbox"]
                conf = h["confianza"]
                clase_heces = h.get("clase", "Heces/Postura")
                cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (0, 165, 255), 2) # Naranja
                cv2.putText(frame, f"ALERTA: {clase_heces} ({conf:.2f})", (hx1, hy1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                eventos_del_frame.append(f"💩 ¡ALERTA HECES/POSTURA! Detectado: {clase_heces} (Conf: {conf:.2f})")

        out.write(frame)
        
        # Imprimir resumen del frame si ocurrió algo interesante
        if eventos_del_frame:
            print(f"[{frame_count}] " + " | ".join(eventos_del_frame))
        
        # Opcional: mostrar el video en vivo (descomenta estas lineas si quieres verlo en vivo)
        # cv2.imshow("Camara de Seguridad", frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    cap.release()
    out.release()
    # cv2.destroyAllWindows()
    print(f"\nProcesamiento terminado. Video guardado en: {OUTPUT_VIDEO_PATH.resolve()}")

if __name__ == "__main__":
    main()
