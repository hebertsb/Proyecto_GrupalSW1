# test_imagen.py
import requests
import sys
import json

# La imagen que quieres analizar (cambia la ruta)
imagen_path = r"C:\Users\HP\Downloads\prueba2cagando.jpg"

# Si pasas una imagen como argumento
if len(sys.argv) > 1:
    imagen_path = sys.argv[1]

url = "http://localhost:8000/api/analizar"

with open(imagen_path, "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    
print(json.dumps(response.json(), indent=2, ensure_ascii=False))