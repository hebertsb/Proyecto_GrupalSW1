import time
from collections import defaultdict

_historial: dict = defaultdict(list)   # camara_id -> [{centro, ts, bbox}]
_DIST_PX   = 120   # radio en píxeles para considerar "misma zona"
_MAX_SEG   = 300   # tiempo máximo de historial (5 min)


def verificar_merodeo(detecciones: list, camara_id, umbral_seg: int = 30) -> list:
    """
    Retorna alertas de merodeo cuando una persona permanece en la misma
    zona de la imagen durante más de `umbral_seg` segundos consecutivos.
    """
    ahora = time.time()
    clave = str(camara_id)

    # Limpiar entradas antiguas
    _historial[clave] = [e for e in _historial[clave] if ahora - e["ts"] < _MAX_SEG]

    alertas = []
    for det in detecciones:
        x1, y1, x2, y2 = det["bbox"]
        centro = ((x1 + x2) // 2, (y1 + y2) // 2)

        _historial[clave].append({"centro": centro, "ts": ahora, "bbox": det["bbox"]})

        cercanos = [e for e in _historial[clave] if _dist(e["centro"], centro) < _DIST_PX]
        if len(cercanos) >= 2:
            tiempo_en_zona = ahora - min(e["ts"] for e in cercanos)
            if tiempo_en_zona >= umbral_seg:
                alertas.append({
                    "segundos": round(tiempo_en_zona, 1),
                    "bbox": det["bbox"],
                    "confianza": det["confianza"],
                })
    return alertas


def limpiar_camara(camara_id) -> None:
    _historial[str(camara_id)].clear()


def _dist(p1: tuple, p2: tuple) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
