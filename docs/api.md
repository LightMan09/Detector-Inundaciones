# API SAPO — contrato JSON

El canal de datos es JSON (según `implementacion.odt`): el modelo YOLO publica
sus detecciones y la API las prioriza, alerta y despacha.

- **Archivo del modelo**: `data/live/detecciones.json` (lo escribe
  `Modelo_Entrenado/sapo_json.py` / `monitor_alcantarilla.py`; lo leen la web y la API).
- **Base URL local**: `http://localhost:8000` (docs en `/docs`).

## Health

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio, dispositivos registrados y estado del modelo |

## Detecciones del modelo (Docker YOLO)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/detections` | Detecciones (`?limit=`), sincronizadas con el JSON del modelo |
| POST | `/api/detections` | Publica un lote del modelo — header `X-Model-Token` |
| GET | `/api/detections/summary` | Resumen 24 h (críticas, taponamientos, basura) |

### Payload del modelo

```json
{
  "dispositivo_id": "camara_modelo_01",
  "detections": [
    {
      "evento_id": "YOLO-20261017-000047",
      "timestamp": "2026-10-17T18:32:00+00:00",
      "dispositivo_id": "camara_modelo_01",
      "origen": "yolo_docker",
      "clase": "agua",
      "clase_modelo": "con_agua",
      "estado": "INUNDADA",
      "confianza": 0.94,
      "nivel_agua_cm": 55.0,
      "cobertura_basura_pct": 0.0,
      "drena_lento": false,
      "tiempo_drenaje_s": null,
      "localizacion_x": 11.1,
      "localizacion_y": 16.2,
      "upz": "UPZ 74 Engativá",
      "barrio": "Porvenir",
      "frame_ref": "Modelo_Entrenado/dataset_sapo_v2/images/test/2_xxx.jpg"
    }
  ]
}
```

Notas:

- `clase_modelo` es la clase cruda del modelo entrenado: `limpia`, `tapada`, `con_agua`.
- `estado` es el estado del monitor: `LIMPIA`, `BASURA`, `INUNDADA`, `DRENANDO`, `SIN_DET`.
- `nivel_agua_cm` se estima del área de la caja de `con_agua` sobre el frame.
- **Sin geolocalización exacta**: `localizacion_x` / `localizacion_y` (0-100) se
  generan aleatorias sobre el mapa y de ahí se derivan `upz` y `barrio`.

Cada detección crítica o con drenaje lento genera alerta para EAAB / IDIGER /
Movilidad / aseo.

## Cámaras / firewall IoT

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/cameras` | Registro de dispositivos (arranca vacío) |
| POST | `/api/cameras` | Alta de dispositivo (valida MAC, IP y posición) |
| POST | `/api/cameras/ingest` | Push de la cámara — solo dispositivos registrados |

Si el dispositivo (id, MAC o IP) no está en el registro se responde `403
device_not_allowed`. El registro se persiste en `data/live/camaras.json`.

## Zonas y priorización (derivadas del JSON del modelo)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/zones` | Ranking de UPZ por riesgo (calculado con las detecciones) |
| GET | `/api/zones/upz` | Catálogo de las 9 UPZ del piloto |
| GET | `/api/zones/critical` | Puntos críticos (`?min_risk=`) |
| GET | `/api/zones/{zona_id}` | Detalle de UPZ |

## Alertas y despacho (ciclo "Actuar")

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/alerts` | Alertas generadas por detecciones críticas |
| POST | `/api/alerts` | Alerta manual del COE Engativá |
| POST | `/api/dispatch` | Órdenes y rutas para camiones de presión-succión |

## Seguridad

- `X-Model-Token`: token del modelo para publicar detecciones (`SAPO_MODEL_TOKEN`).
- Firewall de dispositivos en el canal de push de cámaras.
- Rate limiting global por IP (`SAPO_MAX_REQUESTS_PER_MINUTE`).
