import cv2
from ultralytics import YOLO
from pathlib import Path

# Cuando termine de entrenar, asegúrate de que esta ruta sea la correcta (fíjate si terminó en detector_correa-3)
MODELO_CORREA = r"runs\detect\detector_correa-3\weights\best.pt"
IMAGEN_PRUEBA = "prueba.jpg" # Pon aquí el nombre de alguna foto con un perro que tengas a mano

def probar_modelo():
    if not Path(MODELO_CORREA).exists():
        print(f"❌ Aún no se ha generado el modelo en {MODELO_CORREA}")
        return

    print("Cargando tu nuevo modelo de correa...")
    modelo = YOLO(MODELO_CORREA)
    
    print(f"Analizando imagen: {IMAGEN_PRUEBA}")
    resultados = modelo(IMAGEN_PRUEBA)
    
    # Mostrar resultados
    for r in resultados:
        im_array = r.plot() # Esto dibuja las cajas automáticamente
        
        cv2.imshow("Prueba de Correa", im_array)
        print("Presiona cualquier tecla en la ventana de la imagen para cerrar...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    probar_modelo()
