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
                
                if nombre_clase in ["Dog-without-Leash", "Dangerous_Dogs"] and conf >= 0.05:
                    print(f"[YOLO Correa] Detectó: {nombre_clase} ({conf:.2f})")
                    cajas_sueltos.append({"bbox": [x1, y1, x2, y2], "confianza": conf})
                elif nombre_clase == "dog leash" and conf >= 0.05:
                    print(f"[YOLO Correa] Detectó: {nombre_clase} ({conf:.2f})")
                    cajas_correa.append({"bbox": [x1, y1, x2, y2], "confianza": conf})

        # 1. Filtrar correas que son alucinaciones (cuando el modelo duda y también predice suelto)
        for c in cajas_correa:
            es_alucinacion = False
            cx1, cy1, cx2, cy2 = c["bbox"]
            ccx, ccy = (cx1 + cx2)/2, (cy1 + cy2)/2
            cw, ch = cx2 - cx1, cy2 - cy1
            
            for s in cajas_sueltos:
                sx1, sy1, sx2, sy2 = s["bbox"]
                scx, scy = (sx1 + sx2)/2, (sy1 + sy2)/2
                dist = ((scx - ccx)**2 + (scy - ccy)**2)**0.5
                # Si ambas cajas apuntan al mismo perro, le damos prioridad absoluta a "Suelto"
                # porque el modelo está muy sesgado a predecir correas falsas.
                if dist < max(cw, ch) * 1.5:
                    es_alucinacion = True
                    break
            
            if not es_alucinacion:
                correas_validas.append(c)
                
        # 2. Los sueltos siempre son válidos si pasaron el filtro inicial
        sueltos_validos = cajas_sueltos
                
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
