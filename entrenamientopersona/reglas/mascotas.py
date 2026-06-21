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
        dueno_cerca = False
        px1, py1, px2, py2 = p["bbox"]
        pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
        
        for h in personas_baja_conf:
            hx1, hy1, hx2, hy2 = h["bbox"]
            hcx, hcy = (hx1 + hx2) / 2, (hy1 + hy2) / 2
            
            dist = ((hcx - pcx)**2 + (hcy - pcy)**2)**0.5
            if dist < umbral_distancia:
                dueno_cerca = True
                break

        # Lógica balanceada para cubrir todos los casos (incluyendo videos POV)
        if not p["suelto"]:
            # El modelo YOLO dice que SÍ HAY CORREA.
            # En videos POV (primera persona), el dueño no sale en cámara, pero la correa se ve clara.
            # Si la confianza de la correa es alta (ej. > 0.35), confiamos ciegamente en el modelo.
            if p["confianza"] < 0.35:
                # Si la confianza es baja, puede ser una "alucinación" en un perro callejero.
                # Exigimos confirmación geométrica: si no hay humano cerca, asumimos que es suelto.
                if not dueno_cerca:
                    p["suelto"] = True
        else:
            # El modelo YOLO dice que el perro está SUELTO (no vio la correa).
            # Si vemos al dueño pegado al perro, asumimos que la IA falló y sí tiene correa.
            if dueno_cerca:
                p["suelto"] = False
            
        if p["suelto"]:
            alertas.append({
                "confianza": p["confianza"]
            })
            
    return alertas
