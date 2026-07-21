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
    """Corrige dígitos OCR en posiciones de letra: 0→O, 1→I, 5→S, 8→B."""
    def _fix(s: str) -> str:
        return s.replace("0", "O").replace("1", "I").replace("5", "S").replace("8", "B")
    # DDDD + LLL
    m = re.match(r"^(\d{3,4})([A-Z0-9]{2,3})$", c)
    if m:
        return m.group(1) + _fix(m.group(2))
    # LLL + DDDD
    m = re.match(r"^([A-Z0-9]{2,3})(\d{3,4})$", c)
    if m:
        return _fix(m.group(1)) + m.group(2)
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

    @staticmethod
    def _mejorar(img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        eq = clahe.apply(gray)
        sharp = cv2.filter2D(eq, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
        return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)

    def _ocr(self, img: np.ndarray) -> list:
        return self.reader.readtext(
            img, detail=1,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            min_size=10,
            text_threshold=0.3,
            low_text=0.25,
        )

    def buscar_placa_en_imagen(self, img_bgr: np.ndarray, conf_min: float = 0.25) -> dict:
        """OCR directo sobre imagen — intenta color y versión mejorada (CLAHE+sharpen)."""
        if img_bgr is None or img_bgr.size == 0:
            return {"placa": None, "texto_raw": "", "confianza": 0.0,
                    "legible": False, "formato_valido": False}
        resultado = self._ocr(img_bgr)
        print(f"[SIVIC] EasyOCR raw ({img_bgr.shape[:2]}): {[(r[1], round(r[2],2)) for r in resultado]}")
        if not resultado:
            resultado = self._ocr(self._mejorar(img_bgr))
            print(f"[SIVIC] EasyOCR CLAHE ({img_bgr.shape[:2]}): {[(r[1], round(r[2],2)) for r in resultado]}")
        for (_, texto, conf) in resultado:
                limpio = self._limpiar(texto)
                m = _PATRON_BUSCAR.search(limpio)
                if m:
                    candidato = _corregir_candidato(m.group())
                    if _PATRON_BO.match(candidato) and conf >= conf_min:
                        return {
                            "placa":          candidato,
                            "texto_raw":      limpio,
                            "confianza":      round(conf, 3),
                            "legible":        True,
                            "formato_valido": True,
                        }
        return {"placa": None, "texto_raw": "", "confianza": 0.0,
                "legible": False, "formato_valido": False}

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
