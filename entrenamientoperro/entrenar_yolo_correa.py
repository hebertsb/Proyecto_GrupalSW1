from ultralytics import YOLO
import os

def main():
    # 1. Cargar el modelo base YOLOv8 nano
    # (Puedes usar yolov8s.pt o yolov8m.pt si quieres un modelo más preciso pero más pesado)
    print("Cargando modelo base YOLOv8n...")
    model = YOLO("yolov8n.pt")
    
    # 2. Definir la ruta al archivo data.yaml del dataset que descargaste
    # ¡IMPORTANTE! Actualiza esta ruta con la que te imprimió el script 'descargar_dataset.py'
    data_yaml_path = r"pet-leash-2\data.yaml" # <--- RUTA DEL DATASET GRANDE
    
    if not os.path.exists(data_yaml_path):
        print(f"Error: No se encuentra el archivo '{data_yaml_path}'.")
        print("Asegúrate de copiar la ruta exacta que te dio el script de descarga de Roboflow.")
        return

    print(f"Iniciando entrenamiento con: {data_yaml_path}")
    
    # 3. Entrenar el modelo
    # Esto descargará la arquitectura y comenzará el entrenamiento.
    results = model.train(
        data=data_yaml_path,
        epochs=50,           # Cantidad de pasadas completas por los datos (puedes subirlo a 100)
        imgsz=640,           # Resolución de las imágenes de entrenamiento
        batch=16,            # Cuántas imágenes procesa a la vez (bajar si te quedas sin memoria VRAM)
        name="detector_correa", # Carpeta donde se guardarán los resultados (runs/detect/detector_correa)
        device="cpu",        # Cambia a 0 si tienes una tarjeta gráfica NVIDIA para que sea mucho más rápido
        patience=15          # Si el modelo no mejora en 15 épocas, se detiene temprano
    )
    
    print("\n¡Entrenamiento finalizado!")
    print("Tus pesos entrenados (best.pt) estarán dentro de la carpeta 'runs/detect/detector_correa/weights/'")

if __name__ == "__main__":
    main()
