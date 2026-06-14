import cv2
import numpy as np


def punto_en_zona(cx: float, cy: float, puntos: list) -> bool:
    poly = np.array(puntos, dtype=np.float32)
    return cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0


def verificar_zonas(detecciones: list, zonas: list, alto: int, ancho: int) -> list:
    """
    detecciones : [{bbox:[x1,y1,x2,y2], confianza, ...}]
    zonas       : [{nombre, puntos:[[x,y],...], normalizado:bool}]
    Retorna lista de violaciones encontradas.
    """
    violaciones = []
    for det in detecciones:
        x1, y1, x2, y2 = det["bbox"]
        # Pie de persona = centro inferior del bbox
        cx = (x1 + x2) / 2
        cy = float(y2)

        for zona in zonas:
            puntos = zona["puntos"]
            if zona.get("normalizado", False):
                puntos = [[p[0] * ancho, p[1] * alto] for p in puntos]

            if punto_en_zona(cx, cy, puntos):
                violaciones.append({
                    "zona": zona.get("nombre", "zona"),
                    "bbox": det["bbox"],
                    "confianza": det["confianza"],
                })
    return violaciones
