def verificar_mascota_suelta(perros: list, personas_baja_conf: list, alto: int, ancho: int) -> list:
    """
    Verifica si los perros detectados están realmente sueltos.
    Si el modelo YOLO detecta 'dog leash' (suelto=False), usamos una heurística geométrica
    para buscar si hay un humano cerca. Si no lo hay, asumimos que el modelo falló
    o el dueño soltó la correa, y forzamos suelto=True.
    
    Devuelve lista de alertas de perros sueltos.
    Modifica el diccionario original de 'perros' actualizando su campo 'suelto'.
    """
    alertas = []
    
    # Umbral dinámico: 45% de la diagonal de la pantalla
    umbral_distancia = ((alto**2 + ancho**2)**0.5) * 0.45

    for p in perros:
        # Independientemente de lo que diga el modelo YOLO (que puede fallar),
        # usamos la heurística geométrica como la fuente de la verdad absoluta.
        
        dueno_cerca = False
        px1, py1, px2, py2 = p["bbox"]
        pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
        
        for h in personas_baja_conf:
            hx1, hy1, hx2, hy2 = h["bbox"]
            hcx, hcy = (hx1 + hx2) / 2, (hy1 + hy2) / 2
            
            # Distancia euclidiana
            dist = ((hcx - pcx)**2 + (hcy - pcy)**2)**0.5
            
            if dist < umbral_distancia:
                dueno_cerca = True
                break

        # Regla de oro geométrica:
        # Si hay un humano cerca, el perro NO está suelto (tiene dueño, ignorar modelo YOLO).
        # Si NO hay humanos cerca, el perro SÍ está suelto (ignorar modelo YOLO).
        p["suelto"] = not dueno_cerca
            
        if p["suelto"]:
            alertas.append({
                "confianza": p["confianza"]
            })
            
    return alertas
