"""Contrato del puente YOLO → JSON de la web (Modelo_Entrenado/sapo_json.py)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PUENTE = RAIZ / "Modelo_Entrenado" / "sapo_json.py"


@pytest.fixture(scope="module")
def sapo_json():
    spec = importlib.util.spec_from_file_location("sapo_json", PUENTE)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_evento_con_posicion_aleatoria(sapo_json, tmp_path):
    emisor = sapo_json.SapoEmisor(salida=tmp_path / "detecciones.json", semilla=7)
    e1 = emisor.nuevo_evento("con_agua", 0.9, area_frac=0.5, estado="INUNDADA")
    e2 = emisor.nuevo_evento("con_agua", 0.9, area_frac=0.5, estado="INUNDADA")

    # Posiciones aleatorias (sin geolocalización) dentro del mapa
    for e in (e1, e2):
        assert 0 <= e["localizacion_x"] <= 100
        assert 0 <= e["localizacion_y"] <= 100
        assert e["upz"].startswith("UPZ ")
        assert e["barrio"]
        assert e["clase"] == "agua"
        assert e["clase_modelo"] == "con_agua"
        assert e["nivel_agua_cm"] > 0
    assert (e1["localizacion_x"], e1["localizacion_y"]) != (
        e2["localizacion_x"], e2["localizacion_y"]
    )


def test_evento_basura_y_limpia(sapo_json, tmp_path):
    emisor = sapo_json.SapoEmisor(salida=tmp_path / "detecciones.json", semilla=3)
    basura = emisor.nuevo_evento("tapada", 0.8, area_frac=0.6, estado="BASURA")
    assert basura["clase"] == "basura"
    assert basura["cobertura_basura_pct"] == 60.0
    assert basura["nivel_agua_cm"] == 0.0

    limpia = emisor.nuevo_evento("limpia", 0.7, area_frac=0.0, estado="LIMPIA")
    assert limpia["clase"] == "limpia"


def test_guarda_json_para_la_web(sapo_json, tmp_path):
    salida = tmp_path / "live" / "detecciones.json"
    emisor = sapo_json.SapoEmisor(salida=salida, semilla=1, modelo="best.pt")
    emisor.cargar()
    emisor.registrar(
        emisor.nuevo_evento("con_agua", 0.9, area_frac=0.3, estado="DRENANDO", drena_lento=True)
    )

    data = json.loads(salida.read_text(encoding="utf-8"))
    assert data["origen"] == "yolo"
    assert data["total"] == 1
    evento = data["detecciones"][0]
    assert evento["drena_lento"] is True
    assert evento["estado"] == "DRENANDO"

    # Reanudar el historial no duplica ni pierde eventos
    otro = sapo_json.SapoEmisor(salida=salida, semilla=1)
    otro.cargar()
    assert len(otro.eventos) == 1


def test_zona_se_deriva_de_la_posicion(sapo_json):
    upz, barrio = sapo_json.zona_para_xy(17, 26)
    assert upz.startswith("UPZ 74")
    assert barrio
    upz2, _ = sapo_json.zona_para_xy(66, 41)
    assert upz2.startswith("UPZ 26")


def test_limpiar_reportes(sapo_json, tmp_path, monkeypatch):
    salida = tmp_path / "detecciones.json"
    emisor = sapo_json.SapoEmisor(salida=salida, semilla=5)
    emisor.registrar(emisor.nuevo_evento("con_agua", 0.9, area_frac=0.4, estado="INUNDADA"))
    assert json.loads(salida.read_text(encoding="utf-8"))["total"] == 1

    monkeypatch.setattr(
        "sys.argv", ["sapo_json.py", "--limpiar", "--salida", str(salida)]
    )
    sapo_json.main()
    data = json.loads(salida.read_text(encoding="utf-8"))
    assert data["total"] == 0
    assert data["detecciones"] == []
