# test_api.py
import requests
import json
from pathlib import Path

# Imagen local del dataset de Stanford Dogs
imagen_path = r"D:\SW1\entrenamientoperro\data\raw\stanford_dogs\Images\n02085620-Chihuahua\n02085620_10074.jpg"
url = "http://127.0.0.1:8000/api/analizar"

if not Path(imagen_path).exists():
    print(f"Error: No existe la imagen en {imagen_path}")
    exit()

print(f"Enviando imagen para analisis: {imagen_path}")
with open(imagen_path, "rb") as f:
    files = {"file": f}
    try:
        response = requests.post(url, files=files)
        if response.status_code == 200:
            print("Respuesta recibida con exito:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Error del servidor ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"Error de conexion: {e}")
