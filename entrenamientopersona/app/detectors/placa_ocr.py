import re

import cv2
import numpy as np

# Formatos bolivianos:
#   1154AER / 4898ELK  → 4 dígitos + 3 letras  (2000 a hoy, más común)
#   824EDH             → 3 dígitos + 3 letras  (1997+)
#   CAL280 / SEK000    → 3 letras  + 3 dígitos (1987-1997)
_PATRON_BO      = re.compile(r"^(\d{3,4}[A-Z]{2,3}|[A-Z]{2,3}\d{3,4})$")
_PATRON_BUSCAR  = re.compile(r"\d{3,4}[A-Z0-9]{2,3}|[A-Z0-9]{2,3}\d{3,4}")


def _corregir_candidato(c: str) -> str:
    """1→L y 0→O en posiciones de letra dentro de la placa boliviana."""
    # DDDD + LLL
    m = re.match(r"^(\d{3,4})([A-Z0-9]{2,3})$", c)
    if m:
        return m.group(1) + m.group(2).replace("1", "L").replace("0", "O")
    # LLL + DDDD
    m = re.match(r"^([A-Z0-9]{2,3})(\d{3,4})$", c)
    if m:
        return m.group(1).replace("1", "L").replace("0", "O") + m.group(2)
    return c


class PlacaOCR:
    """
    Lee el texto de una región de placa usando EasyOCR.

    Uso:
        ocr   = PlacaOCR()
        texto = ocr.leer(crop_bgr)
        # → {"placa": "1154AER", "confianza": 0.87, "legible": True, "formato_valido": True}
    """

    def __init__(self, conf_minima: float = 0.50):
        import easyocr
        self.reader      = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        self.conf_minima = conf_minima

    def _preprocesar(self, crop: np.ndarray) -> np.ndarray:
        gris     = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        mejorado = clahe.apply(gris)
        return cv2.fastNlMeansDenoising(mejorado, h=10)

    @staticmethod
    def _limpiar(texto: str) -> str:
        # Quitar todo excepto letras y dígitos (Bolivia no usa guion en formato actual)
        return re.sub(r"[^A-Z0-9]", "", texto.upper().strip())

    def leer(self, crop_bgr: np.ndarray) -> dict:
        """
        Recibe el recorte BGR de la región de placa (salida de PlacaDetector).
        Devuelve:
          {
            "placa":          "1154AER" | None,
            "texto_raw":      str,
            "confianza":      float,
            "legible":        bool,
            "formato_valido": bool,
          }
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return {"placa": None, "texto_raw": "", "confianza": 0.0,
                    "legible": False, "formato_valido": False}

        proc      = self._preprocesar(crop_bgr)
        resultado = self.reader.readtext(
            proc, detail=1,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )

        texto_raw = "".join([r[1] for r in resultado])
        texto     = self._limpiar(texto_raw)
        confianza = float(np.mean([r[2] for r in resultado])) if resultado else 0.0

        # Buscar patrón dentro del texto completo (OCR puede capturar texto extra)
        placa_encontrada = None
        m = _PATRON_BUSCAR.search(texto)
        if m:
            candidato = _corregir_candidato(m.group())
            if _PATRON_BO.match(candidato):
                placa_encontrada = candidato

        es_valida = placa_encontrada is not None
        legible   = confianza >= self.conf_minima and es_valida

        return {
            "placa":          placa_encontrada if legible else None,
            "texto_raw":      texto,
            "confianza":      round(confianza, 3),
            "legible":        legible,
            "formato_valido": es_valida,
        }
