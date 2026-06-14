"""
Tests rápidos para el microservicio de personas/vehículos.
Requiere: pip install httpx pytest
Iniciar servidor primero: uvicorn api:app --port 8002 --reload
"""
import httpx

BASE = "http://127.0.0.1:8002"


def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["persona_detector"] is True
    assert data["vehiculo_detector"] is True
    print("✅ /health OK:", data)


def test_detect_personas(imagen_path: str = "test.jpg"):
    with open(imagen_path, "rb") as f:
        r = httpx.post(f"{BASE}/detect/personas", files={"file": f})
    assert r.status_code == 200
    data = r.json()
    print(f"✅ /detect/personas → {data['personas_detectadas']} personas")
    return data


def test_detect_vehiculos(imagen_path: str = "test.jpg"):
    with open(imagen_path, "rb") as f:
        r = httpx.post(f"{BASE}/detect/vehiculos", files={"file": f})
    assert r.status_code == 200
    data = r.json()
    print(f"✅ /detect/vehiculos → {data['vehiculos_detectados']} vehículos")
    return data


def test_analizar(imagen_path: str = "test.jpg", camara_id: int = 9):
    import json
    zonas = [
        {
            "nombre": "Zona de prueba",
            "puntos": [[0, 0], [640, 0], [640, 480], [0, 480]],
            "normalizado": False,
        }
    ]
    with open(imagen_path, "rb") as f:
        r = httpx.post(
            f"{BASE}/analizar",
            files={"file": f},
            data={"camara_id": camara_id, "zonas_json": json.dumps(zonas), "umbral_merodeo": 5},
        )
    assert r.status_code == 200
    data = r.json()
    print(f"✅ /analizar → alertas: {data['alertas']}, detecciones: {len(data['detecciones'])}")
    return data


if __name__ == "__main__":
    print("─── SIVIC Persona/Vehículo Microservice — Tests ───")
    test_health()
    # test_detect_personas("ruta/a/imagen.jpg")
    # test_analizar("ruta/a/imagen.jpg")
