from pathlib import Path          # rutas cómodas en Windows
import torch                      # para detectar si hay GPU con CUDA
from ultralytics import YOLO      # YOLOv8

RUTA_YAML = r"C:/Users/sneid/OneDrive/Escritorio/dataser/dataset_sapo_v2/data.yaml"  # yaml del dataset corregido
CARPETA_RUNS = Path(__file__).parent / "runs"   # aquí quedarán los resultados, junto a este script

def main():
    usa_gpu = torch.cuda.is_available()          # True si PyTorch ve una GPU NVIDIA
    if usa_gpu:
        nombre_gpu = torch.cuda.get_device_name(0)                                 # nombre de la GPU
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3       # memoria de video en GB
        print(f"GPU detectada: {nombre_gpu} ({vram_gb:.1f} GB)")
        modelo_base = "yolov8s.pt" if vram_gb >= 6 else "yolov8n.pt"   # 's' es más preciso si hay VRAM suficiente
        batch = 16 if vram_gb >= 6 else 8                              # batch más chico si hay poca VRAM
        imgsz, epochs, device, workers = 640, 100, 0, 2                # configuración completa para GPU
    else:
        print("No se detectó GPU: se entrena en CPU (será lento)")
        modelo_base = "yolov8n.pt"                                     # el modelo más liviano
        batch = 8                                                      # batch pequeño para no saturar la RAM
        imgsz, epochs, device, workers = 512, 50, "cpu", 2             # imagen y épocas reducidas para CPU

    modelo = YOLO(modelo_base)                   # carga los pesos preentrenados (transfer learning)
    modelo.train(
        data=RUTA_YAML,                          # dataset corregido
        epochs=epochs,                           # máximo de épocas
        patience=20,                             # se detiene si val no mejora en 20 épocas seguidas
        imgsz=imgsz,                             # tamaño de entrada
        batch=batch,                             # imágenes por lote
        device=device,                           # GPU o CPU
        workers=workers,                         # hilos de carga de datos (bajo para evitar problemas en Windows)
        project=str(CARPETA_RUNS),               # carpeta de salida fija, para encontrar best.pt fácil
        name="modelo_sapo_v2",                   # nombre de esta corrida
        seed=0,                                  # semilla fija para poder repetir el entrenamiento
        cache="ram",                             # guarda las imágenes en RAM (quita esta línea si tienes poca RAM)
        close_mosaic=10,                         # apaga el mosaic en las últimas 10 épocas, estabiliza el final
        degrees=10.0,                            # rotaciones leves: la cámara real nunca queda perfectamente recta
        flipud=0.0,                              # sin volteo vertical (una alcantarilla no aparece de cabeza)
        plots=True,                              # genera la matriz de confusión y las curvas
    )

    ruta_best = Path(modelo.trainer.save_dir) / "weights" / "best.pt"   # mejor modelo según val
    print(f"\nMejor modelo guardado en: {ruta_best}")

    mejor = YOLO(str(ruta_best))                 # cargamos el mejor modelo para evaluarlo
    m = mejor.val(
        data=RUTA_YAML, split="test",            # evaluamos sobre TEST, datos que nunca influyeron en el entrenamiento
        imgsz=imgsz, device=device,
        conf=0.001,                              # umbral bajo: así las curvas PR y F1 son completas
        plots=True, name="eval_test",            # guarda las gráficas de la evaluación en test
    )

    print("\n=== RESULTADOS EN TEST ===")
    print(f"Global -> Precision: {m.box.mp:.3f} | Recall: {m.box.mr:.3f} | mAP50: {m.box.map50:.3f} | mAP50-95: {m.box.map:.3f}")
    for i, idx in enumerate(m.box.ap_class_index):                 # resultados por clase
        p, r, ap50, ap = m.box.class_result(i)                     # precisión, recall, mAP50, mAP50-95 de la clase
        print(f"{m.names[int(idx)]:10s} -> P: {p:.3f} | R: {r:.3f} | mAP50: {ap50:.3f} | mAP50-95: {ap:.3f}")

if __name__ == "__main__":                       # en Windows es obligatorio: evita errores de multiprocesamiento
    main()