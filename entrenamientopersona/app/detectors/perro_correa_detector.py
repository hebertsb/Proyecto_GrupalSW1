import os
from ultralytics import YOLO

MODEL_PATH = os.getenv("PERRO_CORREA_MODEL_PATH", "modelo_correa_nuevo.pt")

class PerroCorreaDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        try:
            self.model = YOLO(model_path)
            print("✅ PerroCorreaDetector (Nuevo) listo")
        except Exception as e:
            print(f"⚠️ Error al cargar PerroCorreaDetector: {e}")
            self.model = None

    def detect(self, img, conf_min: float = 0.40) -> list:
        if self.model is None:
            return []
        
        # SIN agnostic_nms para permitir que ambas clases (suelto y con correa) se detecten simultáneamente si el modelo duda.
        results = self.model(img, verbose=False, iou=0.45)
        
        cajas_sueltos = []
        cajas_correa = []
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < 0.05:
                    continue
                    
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                clase_idx = int(box.cls[0])
                nombre_clase = self.model.names[clase_idx]
                
                if nombre_clase == "Dog-without-Leash" and conf >= 0.15:
                    print(f"[YOLO Correa] Detectó: {nombre_clase} ({conf:.2f})")
                    cajas_sueltos.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                elif nombre_clase == "dog leash" and conf >= 0.05:
                    print(f"[YOLO Correa] Detectó: {nombre_clase} ({conf:.2f})")
                    cajas_correa.append({"bbox": [x1, y1, x2, y2], "confianza": conf})

        # Heurística: Si detecta una correa (dog leash) en la imagen, anulamos las cajas de perro suelto
        # que se superpongan o estén muy cerca, porque el modelo de Roboflow suele confundirse y predecir ambas.
        perros_finales = []
        correas_validas = []
        sueltos_validos = []
        
        # 1. Filtrar correas que son alucinaciones (cuando el "suelto" es muchísimo más seguro)
        for c in cajas_correa:
            es_alucinacion = False
            cx1, cy1, cx2, cy2 = c["bbox"]
            ccx, ccy = (cx1 + cx2)/2, (cy1 + cy2)/2
            cw, ch = cx2 - cx1, cy2 - cy1
            
            for s in cajas_sueltos:
                sx1, sy1, sx2, sy2 = s["bbox"]
                scx, scy = (sx1 + sx2)/2, (sy1 + sy2)/2
                dist = ((scx - ccx)**2 + (scy - ccy)**2)**0.5
                if dist < max(cw, ch) * 1.5:
                    if s["confianza"] > c["confianza"] + 0.20:
                        es_alucinacion = True
                        break
            
            if not es_alucinacion:
                correas_validas.append(c)
                
        # 2. Filtrar perros sueltos que en realidad tienen correa válida
        for s in cajas_sueltos:
            es_falso_suelto = False
            sx1, sy1, sx2, sy2 = s["bbox"]
            scx, scy = (sx1 + sx2)/2, (sy1 + sy2)/2
            sw, sh = sx2 - sx1, sy2 - sy1
            
            for c in correas_validas:
                cx1, cy1, cx2, cy2 = c["bbox"]
                ccx, ccy = (cx1 + cx2)/2, (cy1 + cy2)/2
                dist = ((scx - ccx)**2 + (scy - ccy)**2)**0.5
                if dist < max(sw, sh) * 1.5:
                    es_falso_suelto = True
                    break
                    
            if not es_falso_suelto:
                sueltos_validos.append(s)
                
        # 3. Construir la lista final
        for c in correas_validas:
            perros_finales.append({
                "bbox": c["bbox"],
                "confianza": round(c["confianza"], 3),
                "suelto": False
            })
            
        for s in sueltos_validos:
            perros_finales.append({
                "bbox": s["bbox"],
                "confianza": round(s["confianza"], 3),
                "suelto": True
            })
            
        return perros_finales
