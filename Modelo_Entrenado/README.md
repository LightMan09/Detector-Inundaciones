# Monitor de alcantarillas con visión por computadora (YOLOv8)

Proyecto en Python que usa YOLOv8 (Ultralytics) y OpenCV para vigilar una alcantarilla con una cámara web o un video y saber en qué estado está. También mide cuánto tarda en drenar el agua cuando hay inundación y avisa si se demora demasiado.

## Qué hace

El sistema clasifica la alcantarilla en cuatro estados:

| Estado | Cómo se obtiene |
|---|---|
| Limpia | El modelo detecta la clase `limpia` |
| Con basura | El modelo detecta la clase `tapada` |
| Inundada | El modelo detecta la clase `con_agua` |
| Drenando | Se deduce por lógica: el área de la caja de agua baja respecto a su pico |

"Drenando" no es una clase del modelo, porque una foto sola no deja ver si el agua está bajando. Se calcula mirando varios frames seguidos.

Cuando se confirma una inundación arranca un cronómetro. Si el drenaje pasa del umbral (10 segundos para pruebas), sale una alerta visual y sonora sobre el video.

## Por qué la primera versión fallaba

La primera versión solo tenía la clase de agua, así que solo podía decir "hay agua" o "no hay agua" y nunca "limpia". Ahora `limpia` es una clase propia. Si el modelo no detecta nada, el estado es `SIN DETECCION`, que es distinto de `LIMPIA` (puede que la cámara no esté viendo la alcantarilla).

## Estructura de la carpeta

```
dataser/
├── dataset_limpio/          # datasets originales (una sola clase cada uno)
├── dataset_tapado/
├── dataset_inundado/
├── dataset_sapo_v2/         # dataset fusionado y corregido (el que se usa)
├── fusionar_datasets.py     # une los tres datasets y reasigna los ids de clase
├── data.py                  # revisa clases e instancias por partición
├── entrenar.py              # entrenamiento + evaluación en test
├── revisar_errores.py       # guarda las imágenes de test donde el modelo falla
├── monitor_alcantarilla.py  # inferencia en tiempo real con cronómetro y alerta
└── runs/                    # resultados del entrenamiento (aquí queda best.pt)
```

## Dataset

Clases (ids finales):

| Id | Clase |
|---|---|
| 0 | limpia |
| 1 | tapada |
| 2 | con_agua |

Cantidad en `dataset_sapo_v2`:

| Clase | Train | Val | Test |
|---|---|---|---|
| limpia | 126 | 35 | 21 |
| tapada | 61 | 18 | 10 |
| con_agua | 904 | 75 | 20 |

Notas importantes:

- Los tres datasets originales tenían una sola clase (id 0), por eso `fusionar_datasets.py` cambia ese id por 0, 1 o 2 según el dataset.
- `dataset_inundado` usa la carpeta `val` y los otros dos usan `valid`. El script de fusión acepta las dos para que no se pierda ninguna partición (en una versión anterior se perdió el val de `con_agua` por eso).
- Hay fuerte desbalance: `con_agua` tiene muchas más imágenes que las otras clases.
- Como cada clase viene de un dataset distinto, existe el riesgo de que el modelo aprenda el fondo (piso, ángulo, cámara) y no el estado. Hay que confirmarlo con video real.

## Instalación (Windows)

Se recomienda un entorno virtual **fuera de OneDrive** para que no intente sincronizar miles de archivos.

```
python -m venv C:\venvs\sapo
C:\venvs\sapo\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Instalar PyTorch **antes** que ultralytics. Para usar la GPU NVIDIA, el comando exacto se saca de https://pytorch.org/get-started/locally/ (Windows, Pip, versión de CUDA igual o menor a la que muestra `nvidia-smi`). Tiene esta forma:

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

Después el resto:

```
pip install ultralytics opencv-python pyyaml
```

Verificar la GPU:

```
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Debe salir `True`. Si sale `False` o la versión termina en `+cpu`, quedó instalado PyTorch sin CUDA.

## Rutas que hay que revisar o cambiar

Algunas rutas están escritas a mano con el usuario `sneid`. Si cambias de computador, de usuario o mueves la carpeta, hay que ajustarlas:

| Archivo | Qué ruta | Qué hacer |
|---|---|---|
| `entrenar.py` | `RUTA_YAML` (apunta a `C:/Users/sneid/OneDrive/Escritorio/dataser/dataset_sapo_v2/data.yaml`) | Cambiarla por la ruta real del `data.yaml` |
| `dataset_sapo_v2/data.yaml` | Línea `path:` (se escribió como ruta absoluta al crear el dataset) | Editarla si mueves la carpeta del dataset |
| `data.py` | `RUTA_YAML` | Apuntarla a `dataset_sapo_v2` si quieres revisar el dataset nuevo y no el viejo |
| `revisar_errores.py` | `MODELO` (asume `runs/modelo_sapo_v2/weights/best.pt`) | Si Ultralytics creó la carpeta con otro nombre (por ejemplo `modelo_sapo_v22`), corregir el nombre |
| `monitor_alcantarilla.py` | `FUENTE` | `0` para cámara web, o la ruta del video con `r` antes de las comillas |

Rutas que **no** hay que tocar:

- `monitor_alcantarilla.py` busca solo el `best.pt` más reciente dentro de `runs/`.
- `fusionar_datasets.py` toma como base la carpeta donde está el propio script, así que solo necesita que `dataset_limpio`, `dataset_tapado` y `dataset_inundado` estén ahí al lado.

En Windows, las rutas se pueden escribir con `/` o con `\`, pero si usas `\` pon una `r` antes de las comillas (`r"C:\ruta\archivo"`) para que Python no interprete las barras como caracteres especiales.

## Cómo usarlo

1. Revisar el dataset (opcional): `python data.py`
2. Entrenar y evaluar: `python entrenar.py`
   - Detecta si hay GPU y ajusta modelo, batch, tamaño de imagen y épocas.
   - Al final evalúa `best.pt` sobre el test.
3. Ver dónde falla el modelo: `python revisar_errores.py`
   - Guarda las imágenes con error en `errores_test/`.
4. Ejecutar el monitor: `python monitor_alcantarilla.py`
   - Teclas: `q` para salir y `r` para reiniciar el estado y el cronómetro.

## Configuración del monitor

Todo se cambia al inicio de `monitor_alcantarilla.py`:

| Variable | Qué controla |
|---|---|
| `FUENTE` | `0` para cámara web, o la ruta de un video |
| `UMBRAL_DRENAJE_S` | Segundos antes de disparar la alerta (10 en pruebas) |
| `CONF_POR_CLASE` | Confianza mínima de cada clase |
| `VENTANA_VOTOS` | Cuántos frames se usan para votar el estado |
| `SHARE_MIN` | Fracción de votos necesaria para confirmar un estado |
| `BAJADA_DRENANDO` / `SUBIDA_INUNDADA` | Cuánto debe cambiar el área del agua para pasar a DRENANDO o volver a INUNDADA |
| `TIMEOUT_SIN_DET_S` | Tiempo sin detecciones tras el cual se cierra una inundación |

### Cómo decide el estado

- Cada frame aporta una etiqueta (la detección con mayor confianza que pase el umbral de su clase, o "nada").
- El estado cambia solo si una etiqueta tiene al menos el 55 % de los últimos 15 frames. Así no parpadea.
- Máquina de estados del cronómetro: `INUNDADA` -> `DRENANDO` -> `LIMPIA` o `BASURA`.
- La alerta se dispara una sola vez por episodio, cuando el cronómetro pasa el umbral.
- Con un video, el tiempo se calcula con el número de frame y los fps, así los tiempos salen correctos aunque el computador vaya lento.

## Resultados del primer entrenamiento (test)

| Clase | Precisión | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| limpia | 0.781 | 0.681 | 0.712 | 0.500 |
| tapada | 0.651 | 0.900 | 0.779 | 0.616 |
| con_agua | 0.974 | 1.000 | 0.995 | 0.953 |
| Global | 0.802 | 0.860 | 0.829 | 0.690 |

Cómo leerlos:

- `limpia` es la clase más débil (recall 0.68): el modelo se pierde cerca de 1 de cada 3 y en pantalla se vería `SIN DETECCION`.
- `tapada` tiene falsas alarmas y muy pocas imágenes (10 en test), así que su número es poco confiable.
- `con_agua` casi perfecta es sospechoso: puede ser una tarea fácil o puede que el modelo esté aprendiendo el fondo.
- El test es chico (51 instancias en total), así que estos números son de referencia.

## Limitaciones conocidas

- "Drenando" depende de qué encierra la caja de `con_agua`. Si cubre solo el charco, el área baja al drenar y el estado aparece. Si cubre toda la alcantarilla, el sistema pasa de `INUNDADA` directo a `LIMPIA` (el tiempo total se mide igual).
- La prueba de fuga entre particiones solo compara nombres de archivo. Si las imágenes son fotogramas de videos, fotogramas casi iguales pueden estar repartidos entre train y test.
- En pantalla los textos van sin tildes ni ñ porque las fuentes de OpenCV no las dibujan.

## Pendiente

- Alerta por Telegram o correo (por ahora la alerta es visual y sonora).
- Probar con videos que simulen inundación y drenaje.
- Mejorar `limpia` y `tapada`: más imágenes, más variedad de luz y ángulo, y revisar los errores de `errores_test/`.
- Confirmar con video real que el modelo no depende del fondo.
