from roboflow import Roboflow

print("Iniciando descarga del NUEVO dataset (dog-leash-2)...")
rf = Roboflow(api_key="QPWqjFMwPLn2Tb9k4RNo")
project = rf.workspace("2022-capstone-design").project("dog-leash-2")
version = project.version(5)
dataset = version.download("yolov8")

print(f"\n¡Nuevo dataset descargado con éxito!")
print(f"Ubicación: {dataset.location}")
