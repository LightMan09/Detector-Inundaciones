# Arquitectura SAPO

Implementación de la infraestructura descrita en `src/implementacion.odt`
para el piloto de Engativá / Humedal Jaboque, con el modelo ya entrenado en
`Modelo_Entrenado/` (YOLOv8: clases `limpia`, `tapada`, `con_agua`).

## Flujo: modelo → JSON → web

```
 cámaras IoT (fijas, móviles/ngrok, camiones)        ciudadanos (WhatsApp)
        │ push RTSP/OpenCV                              │ foto
        ▼                                               ▼
┌────────────────────────────────┐          validación IA de reportes
│ Modelo_Entrenado (YOLO best.pt)│                        │
│ monitor_alcantarilla.py        │                        │
│   + sapo_json.py (puente)      │                        │
└───────────────┬────────────────┘                        │
                │ escribe data/live/detecciones.json      │
                │ (localizacion_x/y ALEATORIAS: sin GPS)  │
                ├──────────────────────────────┐          │
                ▼                              ▼          ▼
      ┌──────────────────┐            ┌──────────────────────────┐
      │ visual/index.html│◀── JSON ───│ API SAPO (src/rally)     │
      │ (tablero usuario)│            │ prioriza · alerta · ruta │
      └──────────────────┘            └──────────────────────────┘
                ▲                              │
                └── POST /api/detections ──────┘ (X-Model-Token)
```

- **`data/live/detecciones.json`** es la única fuente de datos del tablero:
  lo escribe el modelo y lo leen la web y la API (sin JSONs precargados).
- **Posición**: el modelo no tiene GPS, así que cada evento se coloca con
  `localizacion_x` / `localizacion_y` aleatorias sobre el mapa de Engativá; la
  UPZ y el barrio se derivan de esa posición (regiones aproximadas).
- **Canal en vivo**: `sapo_json.py` además puede hacer `POST /api/detections`
  para que la API genere alertas y órdenes de despacho.
- **Firewall IoT**: los push de cámaras solo se aceptan si el dispositivo está
  registrado (`POST /api/cameras`).

## Capas (el patrón `app/` del documento = `src/rally/`)

| Capa | Responsabilidad | En SAPO |
|---|---|---|
| `api/` | Recibir HTTP, validar, responder | `/api/detections` recibe el JSON del modelo |
| `core/` | Config, seguridad, constantes | Firewall de dispositivos, umbrales de severidad |
| `models/` | Entidades del dominio | `Camera`, `Detection`, `CriticalPoint`, `Zone` |
| `schemas/` | Contratos HTTP | `DetectionCreate`, `AlertResponse`, `DispatchOrder` |
| `services/` | Lógica de negocio | Score de riesgo, alertas EAAB/IDIGER, rutas de camiones |
| `repositories/` | Acceso a datos | Sync con `data/live/detecciones.json`; zonas derivadas |
| `tasks/` | Background jobs | Purga de detecciones viejas |
| `utils/` | Helpers puros | `geo.py`, `validators.py` |
| `middleware/` | Cross-cutting | Logging, rate limiting |

## Datos

| Archivo | Quién lo escribe | Contenido |
|---|---|---|
| `data/live/detecciones.json` | `Modelo_Entrenado/sapo_json.py` | Eventos del modelo (clase, estado, nivel, x/y, UPZ, barrio) |
| `data/live/camaras.json` | API (`POST /api/cameras`) | Registro de dispositivos (firewall) |
| `data/maps/engativa_jaboque.png` | — | Mapa oficial de Engativá del tablero |

## Modelo (Modelo_Entrenado)

- `runs/modelo_sapo_v2-2/weights/best.pt` — entrenado con `dataset_sapo_v2`
  (imágenes de alcantarillas: limpia / tapada / con_agua).
- `monitor_alcantarilla.py` — inferencia en vivo con máquina de estados
  (INUNDADA → DRENANDO → LIMPIA/BASURA) y alerta de drenaje lento; publica cada
  cambio de estado como evento JSON.
- `sapo_json.py` — construye los eventos SAPO (posición aleatoria + UPZ/barrio),
  escribe el JSON de la web y opcionalmente hace POST a la API.

## Flujo "de reaccionar a prevenir"

1. **Detectar** — YOLO clasifica la alcantarilla; si el agua no baja se infiere
   taponamiento interno sin sensores en la tubería.
2. **Priorizar** — score 0-100 por UPZ (nivel de agua, basura, repetición).
3. **Actuar** — alertas a EAAB/IDIGER/Movilidad/aseo + rutas de camiones de
   presión-succión (la cámara del camión detecta más sumideros en su ruta).
4. **Prevenir** — los puntos con mayor repetición alimentan la decisión de
   convertir alcorques en alcorques inundables (comisión ambiental de la JAC).
