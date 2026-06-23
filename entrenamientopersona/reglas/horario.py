from datetime import datetime, time as dtime, timezone, timedelta

# Bolivia = UTC-4
_TZ_BOLIVIA = timezone(timedelta(hours=-4))

def _hora_actual() -> dtime:
    return datetime.now(_TZ_BOLIVIA).time()


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
    Alerta si hay personas en zonas 'horario_restringido' fuera del horario
    permitido. Cada zona puede definir su propio horario en configuracion
    {hora_inicio: "HH:MM", hora_fin: "HH:MM"}; si no, usa los defaults.
    """
    if not detecciones or not zonas:
        return []

    zonas_horario = [z for z in zonas if z.get("nombre") == "horario_restringido"]
    if not zonas_horario:
        return []

    ahora = _hora_actual()
    import cv2
    import numpy as np
    alertas = []
    for d in detecciones:
        x1, y1, x2, y2 = d["bbox"]
        cx = int((x1 + x2) / 2)
        cy = int(y2)
        for zona in zonas_horario:
            cfg = zona.get("configuracion") or {}
            try:
                h_ini = dtime(*map(int, cfg["hora_inicio"].split(":"))) if "hora_inicio" in cfg else hora_permitida_inicio
                h_fin = dtime(*map(int, cfg["hora_fin"].split(":")))    if "hora_fin"    in cfg else hora_permitida_fin
            except (ValueError, AttributeError):
                h_ini, h_fin = hora_permitida_inicio, hora_permitida_fin

            if h_ini <= ahora <= h_fin:
                continue  # dentro del horario permitido para esta zona

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
