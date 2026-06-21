def verificar_mascota_suelta(perros: list, personas_baja_conf: list, alto: int, ancho: int) -> list:
    """
    Verifica si los perros detectados están realmente sueltos.
    Confiamos en la predicción del modelo YOLO de PerroCorreaDetector.
    """
    alertas = []
    
    for p in perros:
        if p.get("suelto", False):
            alertas.append({
                "confianza": p["confianza"]
            })
            
    return alertas
