"""Puente entre el monitor YOLO (Modelo_Entrenado) y la web visual de SAPO.

El modelo no tiene geolocalización exacta: cada evento se coloca con
``localizacion_x`` / ``localizacion_y`` aleatorias sobre el mapa de Engativá y
la UPZ / barrio se derivan de esa posición (regiones aproximadas del mapa).

Salidas (JSON que consume la web):
- ``data/live/detecciones.json`` — historial de eventos del modelo
- POST ``/api/detections`` a la API SAPO (opcional, header ``X-Model-Token``)

Uso:
    python sapo_json.py --imagenes <carpeta>        # corre best.pt sobre imágenes
    python sapo_json.py --simular --n 12            # eventos de prueba sin cámara
    python sapo_json.py --imagenes . --api http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent          # Modelo_Entrenado/
RAIZ = BASE.parent                              # raíz del repo (Rally/)
SALIDA_POR_DEFECTO = RAIZ / "data" / "live" / "detecciones.json"

# Clases del modelo entrenado (dataset_sapo_v2/data.yaml)
NOMBRES_CLASE = {0: "limpia", 1: "tapada", 2: "con_agua"}
CLASE_A_SAPO = {0: "limpia", 1: "basura", 2: "agua"}
# Estados del monitor (monitor_alcantarilla.py) que viajan crudos en el JSON
ESTADOS_MONITOR = ("LIMPIA", "BASURA", "INUNDADA", "DRENANDO", "SIN_DET")

# Estimación de nivel (cm) a partir del área de la caja de agua sobre el frame
NIVEL_CM_POR_AREA = 80.0
NIVEL_CM_MAX = 55.0

# Regiones aproximadas de las UPZ sobre el mapa (localizacion_x/y en %)
# Se usan para etiquetar el evento: la posición real sigue siendo aleatoria.
REGIONES_UPZ = [
    {"zona": "upz74", "codigo": "74", "nombre": "Engativá",
     "x": (2, 32), "y": (10, 38), "centro": (17, 26),
     "barrios": ["Jaboque", "Porvenir", "La Tortigua", "Engativá-Centro",
                 "El Muelle", "Villa Claver"]},
    {"zona": "upz73", "codigo": "73", "nombre": "Garcés Navas",
     "x": (2, 32), "y": (34, 50), "centro": (16, 41),
     "barrios": ["Villas de Granada", "Gran Granada", "Álamos Norte", "Garcés Navas"]},
    {"zona": "upz31", "codigo": "31", "nombre": "Santa Cecilia",
     "x": (22, 48), "y": (26, 48), "centro": (33, 38),
     "barrios": ["Quirigua", "Ciudad Bachué", "Santa Cecilia"]},
    {"zona": "upz72", "codigo": "72", "nombre": "Bolivia",
     "x": (10, 38), "y": (46, 64), "centro": (23, 55),
     "barrios": ["Ciudadela Colsubsidio", "El Cortijo", "Bolivia"]},
    {"zona": "upz30", "codigo": "30", "nombre": "Boyacá Real",
     "x": (26, 52), "y": (42, 60), "centro": (38, 51),
     "barrios": ["Boyacá Real", "La Granja", "Tabora", "Santa Helenita"]},
    {"zona": "upz116", "codigo": "116", "nombre": "Álamos",
     "x": (28, 56), "y": (48, 70), "centro": (42, 58),
     "barrios": ["Álamos Industrial", "Álamos Norte", "Mutis"]},
    {"zona": "upz29", "codigo": "29", "nombre": "Minuto de Dios",
     "x": (40, 66), "y": (32, 54), "centro": (52, 45),
     "barrios": ["Minuto de Dios", "París Gaitán"]},
    {"zona": "upz26", "codigo": "26", "nombre": "Las Ferias",
     "x": (52, 82), "y": (28, 52), "centro": (66, 41),
     "barrios": ["Las Ferias", "Bonanza", "La Estrada", "Metrópolis"]},
    {"zona": "upz105", "codigo": "105", "nombre": "Jardín Botánico",
     "x": (50, 84), "y": (48, 76), "centro": (67, 61),
     "barrios": ["Normandía", "Bosque Popular", "San Joaquín"]},
]


def zona_para_xy(x: float, y: float, rng: random.Random | None = None) -> tuple[str, str]:
    """UPZ y barrio para una posición aleatoria del mapa."""
    rng = rng or random
    candidatas = [
        r for r in REGIONES_UPZ
        if r["x"][0] <= x <= r["x"][1] and r["y"][0] <= y <= r["y"][1]
    ]
    if not candidatas:
        candidatas = sorted(
            REGIONES_UPZ,
            key=lambda r: (x - r["centro"][0]) ** 2 + (y - r["centro"][1]) ** 2,
        )[:1]
    region = min(
        candidatas,
        key=lambda r: (x - r["centro"][0]) ** 2 + (y - r["centro"][1]) ** 2,
    )
    upz = f"UPZ {region['codigo']} {region['nombre']}"
    barrio = rng.choice(region["barrios"])
    return upz, barrio


def nivel_desde_area(area_frac: float) -> float:
    """Convierte el área de la caja de agua (fracción del frame) a cm estimados."""
    return round(min(max(area_frac, 0.0) * NIVEL_CM_POR_AREA, NIVEL_CM_MAX), 1)


class SapoEmisor:
    """Construye eventos SAPO desde el monitor YOLO y los publica como JSON."""

    def __init__(
        self,
        dispositivo_id: str = "camara_modelo_01",
        salida: Path = SALIDA_POR_DEFECTO,
        api_url: str | None = None,
        token: str = "",
        max_eventos: int = 200,
        origen: str = "yolo",
        modelo: str = "",
        semilla: int | None = None,
    ) -> None:
        self.dispositivo_id = dispositivo_id
        self.salida = Path(salida)
        self.api_url = (api_url or "").rstrip("/")
        self.token = token
        self.max_eventos = max_eventos
        self.origen = origen
        self.modelo = modelo
        self.rng = random.Random(semilla)
        self.eventos: list[dict] = []
        self._contador = 0

    # ---------- construcción del evento ----------

    def nuevo_evento(
        self,
        clase_modelo: str,
        confianza: float,
        area_frac: float = 0.0,
        estado: str = "SIN_DET",
        drena_lento: bool = False,
        tiempo_drenaje_s: float | None = None,
        frame_ref: str | None = None,
    ) -> dict:
        """Arma un evento SAPO con posición aleatoria sobre el mapa."""
        self._contador += 1
        x = round(self.rng.uniform(6, 88), 1)      # sin geolocalización exacta: posición random
        y = round(self.rng.uniform(12, 74), 1)
        upz, barrio = zona_para_xy(x, y, self.rng)

        clase_sapo = {
            "limpia": "limpia",
            "tapada": "basura",
            "con_agua": "agua",
        }.get(clase_modelo, "sin_deteccion")

        nivel_cm = nivel_desde_area(area_frac) if clase_modelo == "con_agua" else 0.0
        if clase_modelo == "tapada":
            basura_pct = round(min(max(area_frac, 0.0) * 100.0, 100.0), 1)
        else:
            basura_pct = 0.0

        return {
            "evento_id": f"YOLO-{datetime.now(timezone.utc):%Y%m%d}-{self._contador:06d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dispositivo_id": self.dispositivo_id,
            "origen": "yolo_docker",
            "clase": clase_sapo,
            "clase_modelo": clase_modelo,
            "estado": estado,
            "confianza": round(float(confianza), 3),
            "nivel_agua_cm": nivel_cm,
            "cobertura_basura_pct": basura_pct,
            "drena_lento": bool(drena_lento),
            "tiempo_drenaje_s": tiempo_drenaje_s,
            "localizacion_x": x,
            "localizacion_y": y,
            "upz": upz,
            "barrio": barrio,
            "punto_critico_id": None,
            "frame_ref": frame_ref,
        }

    def registrar(self, evento: dict) -> dict:
        self.eventos.append(evento)
        if len(self.eventos) > self.max_eventos:
            self.eventos = self.eventos[-self.max_eventos:]
        self.guardar()
        self.enviar_api([evento])
        return evento

    # ---------- persistencia ----------

    def guardar(self) -> None:
        self.salida.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "modelo": self.modelo,
            "origen": self.origen,
            "actualizado": datetime.now(timezone.utc).isoformat(),
            "total": len(self.eventos),
            "detecciones": self.eventos,
        }
        tmp = self.salida.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.salida)

    def cargar(self) -> None:
        """Recarga eventos ya publicados (para no perder el historial)."""
        if not self.salida.exists():
            return
        try:
            data = json.loads(self.salida.read_text(encoding="utf-8"))
            self.eventos = list(data.get("detecciones", []))
            self._contador = len(self.eventos)
        except (json.JSONDecodeError, OSError):
            self.eventos = []

    # ---------- canal hacia la API ----------

    def enviar_api(self, eventos: list[dict]) -> None:
        if not self.api_url or not eventos:
            return
        try:
            import urllib.request

            payload = {"dispositivo_id": self.dispositivo_id, "detections": eventos}
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.api_url}/api/detections",
                data=body,
                headers={"Content-Type": "application/json", "X-Model-Token": self.token},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[sapo_json] API {resp.status}: {len(eventos)} evento(s)")
        except Exception as exc:  # la web sigue funcionando con el archivo local
            print(f"[sapo_json] no se pudo enviar a la API ({exc})")


def eventos_simulados(n: int, emisor: SapoEmisor) -> list[dict]:
    """Genera eventos de prueba con la misma forma que produce el modelo."""
    clases = ["con_agua", "tapada", "limpia"]
    estados = {"con_agua": ["INUNDADA", "DRENANDO"], "tapada": ["BASURA"], "limpia": ["LIMPIA"]}
    hechos = []
    for _ in range(n):
        clase = emisor.rng.choice(clases)
        estado = emisor.rng.choice(estados[clase])
        area = emisor.rng.uniform(0.15, 0.7) if clase != "limpia" else 0.0
        evento = emisor.nuevo_evento(
            clase_modelo=clase,
            confianza=emisor.rng.uniform(0.55, 0.95),
            area_frac=area,
            estado=estado,
            drena_lento=(clase == "con_agua" and emisor.rng.random() < 0.4),
            tiempo_drenaje_s=round(emisor.rng.uniform(5, 40), 1) if clase == "con_agua" else None,
        )
        hechos.append(emisor.registrar(evento))
    return hechos


def eventos_desde_imagenes(
    carpeta: Path, emisor: SapoEmisor, conf_min: float = 0.30, imgsz: int = 640
) -> list[dict]:
    """Corre el modelo entrenado (best.pt) sobre una carpeta de imágenes."""
    from ultralytics import YOLO  # import pesado: solo cuando hace inferencia

    modelo_path = max(
        (BASE / "runs").glob("**/weights/best.pt"),
        key=lambda p: p.stat().st_mtime,
        default=None,
    )
    if modelo_path is None:
        raise FileNotFoundError("No encontré runs/**/weights/best.pt")
    emisor.modelo = str(modelo_path.relative_to(RAIZ))
    modelo = YOLO(str(modelo_path))

    carpeta = carpeta.resolve()
    imagenes = sorted(
        p for p in carpeta.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not imagenes:
        raise FileNotFoundError(f"Sin imágenes en {carpeta}")

    hechos = []
    for img in imagenes:
        resultado = modelo.predict(
            str(img), conf=conf_min, imgsz=imgsz, device="cpu", verbose=False
        )[0]
        frame_area = max(resultado.orig_shape[0] * resultado.orig_shape[1], 1)
        mejor, mejor_conf, area_agua = None, 0.0, 0.0
        for box in resultado.boxes:
            clase, conf = int(box.cls[0]), float(box.conf[0])
            if conf > mejor_conf:
                mejor, mejor_conf = clase, conf
            if clase == 2:
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                area_agua = max(area_agua, (x2 - x1) * (y2 - y1) / frame_area)
        if mejor is None:
            continue
        evento = emisor.nuevo_evento(
            clase_modelo=NOMBRES_CLASE[mejor],
            confianza=mejor_conf,
            area_frac=area_agua,
            estado={"limpia": "LIMPIA", "tapada": "BASURA", "con_agua": "INUNDADA"}[
                NOMBRES_CLASE[mejor]
            ],
            frame_ref=str(img.relative_to(RAIZ)),
        )
        hechos.append(emisor.registrar(evento))
    return hechos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica detecciones del modelo como JSON para la web SAPO"
    )
    parser.add_argument("--imagenes", help="carpeta de imágenes para correr best.pt")
    parser.add_argument(
        "--simular", action="store_true", help="genera eventos de prueba (sin cámara)"
    )
    parser.add_argument("--n", type=int, default=12, help="cantidad de eventos en --simular")
    parser.add_argument("--salida", default=str(SALIDA_POR_DEFECTO), help="archivo JSON de salida")
    parser.add_argument("--api", default="", help="URL de la API SAPO (ej. http://localhost:8000)")
    parser.add_argument("--token", default="", help="X-Model-Token de la API")
    parser.add_argument("--dispositivo", default="camara_modelo_01")
    parser.add_argument(
        "--semilla", type=int, default=None, help="semilla para posiciones aleatorias"
    )
    parser.add_argument("--nuevo", action="store_true", help="no continuar el historial existente")
    parser.add_argument(
        "--limpiar", action="store_true", help="borra todos los eventos publicados (reportes)"
    )
    args = parser.parse_args()

    if args.limpiar:
        salida = Path(args.salida)
        salida.parent.mkdir(parents=True, exist_ok=True)
        vacio = {
            "modelo": "",
            "origen": "yolo",
            "actualizado": datetime.now(timezone.utc).isoformat(),
            "total": 0,
            "detecciones": [],
        }
        salida.write_text(json.dumps(vacio, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[sapo_json] historial limpio -> {salida}")
        print(
            "[sapo_json] si la API está corriendo, reiníciala para vaciar "
            "su memoria y las alertas"
        )
        return

    emisor = SapoEmisor(
        dispositivo_id=args.dispositivo,
        salida=Path(args.salida),
        api_url=args.api,
        token=args.token,
        origen="simulacion" if args.simular else "yolo",
        semilla=args.semilla,
    )
    if not args.nuevo:
        emisor.cargar()

    if args.simular:
        hechos = eventos_simulados(args.n, emisor)
    elif args.imagenes:
        hechos = eventos_desde_imagenes(Path(args.imagenes), emisor)
    else:
        parser.error("indica --imagenes <carpeta>, --simular o --limpiar")

    emisor.guardar()
    print(f"[sapo_json] {len(hechos)} evento(s) -> {emisor.salida}")
    if emisor.eventos:
        ultimo = emisor.eventos[-1]
        print(
            f"[sapo_json] último: {ultimo['clase_modelo']} en "
            f"({ultimo['localizacion_x']}, {ultimo['localizacion_y']}) -> "
            f"{ultimo['upz']} / {ultimo['barrio']}"
        )


if __name__ == "__main__":
    main()
