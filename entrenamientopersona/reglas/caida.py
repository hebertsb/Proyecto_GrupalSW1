_RATIO_CAIDA = 2.2  # bbox ancho/alto > 2.2 → persona muy horizontal = posible caída (1.4 generaba falsos positivos con personas sentadas)


def verificar_caida(detecciones: list) -> list:
    """
    Detecta caída si el bbox de una persona es más ancho que alto.
    Devuelve lista de alertas con bbox de la persona caída.
    """
    alertas = []
    for d in detecciones:
        x1, y1, x2, y2 = d["bbox"]
        ancho = x2 - x1
        alto  = y2 - y1
        if alto > 0 and (ancho / alto) >= _RATIO_CAIDA:
            alertas.append({
                "bbox":      d["bbox"],
                "confianza": d["confianza"],
                "ratio":     round(ancho / alto, 2),
            })
    return alertas
