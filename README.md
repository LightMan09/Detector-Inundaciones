# SAPO — Alerta y limpieza preventiva de sumideros (piloto Engativá)

Plataforma que convierte las cámaras de tránsito y los camiones de succión
existentes en sensores activos de encharcamientos y sumideros tapados, prioriza
los puntos críticos con datos y despacha limpieza **antes** de la inundación.

Piloto: **Localidad 10 de Engativá**, ronda del **Humedal Jaboque** y Río Bogotá.

## Flujo de datos (modelo → web)

```
Modelo_Entrenado (best.pt entrenado)
   │  publica JSON  →  data/live/detecciones.json   (x/y aleatorias: sin GPS)
   │  POST /api/detections (X-Model-Token) → alertas + despacho
   ▼
visual/index.html  (tablero)  ·  API FastAPI (src/rally)
```

Cada evento del modelo incluye `clase_modelo` (`limpia`/`tapada`/`con_agua`),
`estado` del monitor (`INUNDADA`/`DRENANDO`/`BASURA`/`LIMPIA`), nivel de agua
estimado, y `localizacion_x` / `localizacion_y` **aleatorias** sobre el mapa de
Engativá (la UPZ y el barrio se derivan de esa posición).

## Estructura

```
├── Modelo_Entrenado/       # YOLOv8 entrenado (limpia/tapada/con_agua)
│   ├── runs/**/weights/best.pt
│   ├── monitor_alcantarilla.py  # inferencia en vivo + máquina de estados
│   └── sapo_json.py             # puente: eventos → JSON de la web (+ POST API)
├── src/rally/              # API FastAPI por capas (patrón "app/" del documento)
│   ├── api/  core/  models/  schemas/  services/
│   ├── repositories/  tasks/  utils/  middleware/
├── visual/                 # tablero del usuario (solo consume JSON)
├── data/
│   ├── live/detecciones.json   # JSON que crea el modelo (fuente de la web)
│   └── maps/engativa_jaboque.png
├── tests/  scripts/  docs/
└── src/alcantarilla_yolo/  # prototipo previo de visión (no se toca)
```

## Arranque rápido

```bash
uv sync
uv run uvicorn rally.main:app --reload
```

- Tablero: http://localhost:8000/
- API docs: http://localhost:8000/docs
- JSON del modelo: http://localhost:8000/data/live/detecciones.json

## Publicar detecciones del modelo

```bash
# una pasada sobre imágenes (genera el JSON de la web)
python Modelo_Entrenado/sapo_json.py --imagenes Modelo_Entrenado/dataset_sapo_v2/images/test

# en vivo, con cámara o video (además envía a la API si hay SAPO_API)
SAPO_API=http://localhost:8000 python Modelo_Entrenado/monitor_alcantarilla.py

# eventos de prueba sin cámara
python Modelo_Entrenado/sapo_json.py --simular --n 12

# resumen del JSON actual
uv run python scripts/seed_data.py
```

Requisitos del modelo: `pip install ultralytics opencv-python torch` (se usó
`runs/modelo_sapo_v2-2/weights/best.pt`, clases `limpia`/`tapada`/`con_agua`).

## Usar la cámara de tu PC

La configuración por defecto de `monitor_alcantarilla.py` ya usa la webcam
(`FUENTE = 0`). Necesitas dos terminales:

```bash
# Terminal 1 — API + tablero
uv sync
uv run uvicorn rally.main:app          # abre http://localhost:8000

# Terminal 2 — modelo con la cámara
cd Modelo_Entrenado
pip install ultralytics opencv-python torch    # solo la primera vez
python monitor_alcantarilla.py                 # FUENTE = 0 = cámara web
```

- Si quieres enviar los eventos también a la API (alertas/despacho), define la
  variable antes de lanzar el monitor:
  - Linux/Mac: `SAPO_API=http://localhost:8000 python monitor_alcantarilla.py`
  - Windows PowerShell: `$env:SAPO_API="http://localhost:8000"; python monitor_alcantarilla.py`
- Si en `src/rally` existe un `.env` con `SAPO_MODEL_TOKEN=...`, añade la misma
  variable en el entorno del monitor: `SAPO_MODEL_TOKEN=...`
- Se abre una ventana con el video: `q` sale, `r` reinicia el cronómetro de drenaje.
- Para ejecutar sin ventana (servidor / video sin GUI): `SAPO_NO_VENTANA=1 python monitor_alcantarilla.py`.
- Cada cambio de estado (INUNDADA / DRENANDO / BASURA / LIMPIA) publica un evento
  en `data/live/detecciones.json`; en el tablero pulsa **Actualizar** (o espera
  30 s) y verás el pin en una posición aleatoria del mapa.
- Para usar un video en vez de la cámara, cambia en el archivo:
  `FUENTE = r"C:/ruta/video.mp4"`.

## Limpiar todos los reportes

```bash
python Modelo_Entrenado/sapo_json.py --limpiar
```

Esto vacía `data/live/detecciones.json`. Si la API estaba corriendo, reiníciala
(Ctrl+C y `uv run uvicorn rally.main:app` de nuevo) para vaciar también su
memoria y las alertas generadas; el tablero quedará en cero.

## Pruebas

```bash
uv run pytest
uv run ruff check src/rally tests scripts Modelo_Entrenado/sapo_json.py
```

## Contratos clave

- **JSON de la web**: `data/live/detecciones.json` lo escribe el modelo y lo
  leen el tablero y la API (misma fuente, sin datos precargados).
- **Canal del modelo**: `POST /api/detections` (header `X-Model-Token`).
- **Firewall IoT**: `POST /api/cameras/ingest` solo acepta dispositivos
  registrados (`POST /api/cameras`).
- **Actuar**: `POST /api/dispatch` asigna rutas a los camiones de presión-succión.

Detalle en [docs/api.md](docs/api.md) y [docs/architecture.md](docs/architecture.md).
