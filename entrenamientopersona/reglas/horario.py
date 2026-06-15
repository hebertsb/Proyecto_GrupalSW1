from datetime import datetime, time as dtime


def _hora_actual() -> dtime:
    return datetime.now().time()


def verificar_intrusion_nocturna(detecciones: list,
                                  hora_inicio: dtime = dtime(22, 0),
                                  hora_fin:    dtime = dtime(6,  0)) -> list:
    """
    Alerta si hay personas detectadas en horario nocturno.
    hora_inicio/fin: rango donde NO se permite presencia (ej. 22:00–06:00).
    El rango puede cruzar medianoche.
    """
    if not detecciones:
        return []

    ahora = _hora_actual()
    # Rango cruza medianoche: activo si hora >= inicio OR hora <= fin
    if hora_inicio > hora_fin:
        es_nocturno = ahora >= hora_inicio or ahora <= hora_fin
    else:
        es_nocturno = hora_inicio <= ahora <= hora_fin

    if not es_nocturno:
        return []

    return [{"hora": ahora.strftime("%H:%M"), "personas": len(detecciones)}]


def verificar_acceso_fuera_horario(detecciones: list, zonas: list,
                                    alto: int, ancho: int,
                                    hora_permitida_inicio: dtime = dtime(8,  0),
                                    hora_permitida_fin:    dtime = dtime(14, 0)) -> list:
    """
    Alerta si hay personas en zonas marcadas como 'horario_restringido'
    fuera del horario permitido.
    """
    if not detecciones or not zonas:
        return []

    zonas_horario = [z for z in zonas if z.get("nombre") == "horario_restringido"]
    if not zonas_horario:
        return []

    ahora = _hora_actual()
    en_horario = hora_permitida_inicio <= ahora <= hora_permitida_fin
    if en_horario:
        return []

    # Hay zonas de horario restringido y estamos fuera del horario permitido
    import cv2
    import numpy as np
    alertas = []
    for d in detecciones:
        x1, y1, x2, y2 = d["bbox"]
        # Centro inferior de la persona
        cx = int((x1 + x2) / 2)
        cy = int(y2)
        for zona in zonas_horario:
            puntos = np.array(zona["puntos"], dtype=np.float32)
            if zona.get("normalizado", False):
                puntos[:, 0] *= ancho
                puntos[:, 1] *= alto
            puntos = puntos.astype(np.int32)
            if cv2.pointPolygonTest(puntos, (cx, cy), False) >= 0:
                alertas.append({
                    "bbox":      d["bbox"],
                    "confianza": d["confianza"],
                    "hora":      ahora.strftime("%H:%M"),
                })
                break
    return alertas
