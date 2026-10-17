"""Valida y resume el JSON que publica el modelo YOLO (data/live/detecciones.json).

Uso:
    uv run python scripts/seed_data.py                  # resume el JSON actual
    uv run python scripts/seed_data.py --regenerar      # corre best.pt sobre las imágenes de test
    uv run python scripts/seed_data.py --api http://localhost:8000   # además lo envía a la API
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "live" / "detecciones.json"
PUENTE = ROOT / "Modelo_Entrenado" / "sapo_json.py"
IMAGENES_TEST = ROOT / "Modelo_Entrenado" / "dataset_sapo_v2" / "images" / "test"


def resumir() -> dict:
    if not LIVE.exists():
        print(f"No existe {LIVE}. Genera el JSON con --regenerar.")
        sys.exit(1)
    data = json.loads(LIVE.read_text(encoding="utf-8"))
    dets = data.get("detecciones", [])
    print("== SAPO · JSON del modelo YOLO ==")
    print(f"archivo     : {LIVE.relative_to(ROOT)}")
    print(f"modelo      : {data.get('modelo', '—')}")
    print(f"origen      : {data.get('origen', '—')}")
    print(f"actualizado : {data.get('actualizado', '—')}")
    print(f"eventos     : {len(dets)}")
    print(f"clases      : {dict(Counter(d.get('clase_modelo') for d in dets))}")
    print(f"estados     : {dict(Counter(d.get('estado') for d in dets))}")
    print(f"UPZ         : {len({d.get('upz') for d in dets})}")
    if dets:
        xs = [d["localizacion_x"] for d in dets]
        ys = [d["localizacion_y"] for d in dets]
        print(f"posición x  : {min(xs)} – {max(xs)} (aleatoria, sin GPS)")
        print(f"posición y  : {min(ys)} – {max(ys)} (aleatoria, sin GPS)")
    faltantes = [
        d.get("evento_id") for d in dets
        if "localizacion_x" not in d or "localizacion_y" not in d or "upz" not in d
    ]
    if faltantes:
        print("AVISO: eventos sin posición/UPZ:", faltantes)
        sys.exit(1)
    print("OK: el JSON del modelo está listo para la web.")
    return data


def regenerar(api: str = "", token: str = "") -> None:
    cmd = [
        sys.executable, str(PUENTE), "--imagenes", str(IMAGENES_TEST),
        "--nuevo", "--semilla", "7",
    ]
    if api:
        cmd += ["--api", api, "--token", token]
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--regenerar", action="store_true", help="correr best.pt y reescribir el JSON"
    )
    parser.add_argument("--api", default="", help="URL de la API (para --regenerar)")
    parser.add_argument("--token", default="", help="X-Model-Token (para --regenerar)")
    args = parser.parse_args()

    if args.regenerar:
        regenerar(args.api, args.token)
    resumir()


if __name__ == "__main__":
    main()
