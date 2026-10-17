"""Tests de integración: zonas derivadas de las detecciones del modelo."""


def _post_evento(client, headers, evento_id, **campos):
    evento = {
        "evento_id": evento_id,
        "dispositivo_id": "camara_modelo_01",
        "clase": "agua",
        "clase_modelo": "con_agua",
        "estado": "INUNDADA",
        "confianza": 0.85,
        "nivel_agua_cm": 30.0,
        "localizacion_x": 27.5,
        "localizacion_y": 38.2,
        "upz": "UPZ 31 Santa Cecilia",
        "barrio": "Quirigua",
    }
    evento.update(campos)
    resp = client.post(
        "/api/detections",
        json={"dispositivo_id": "camara_modelo_01", "detections": [evento]},
        headers=headers,
    )
    assert resp.status_code == 200
    return evento


def test_zones_desde_detecciones(client, model_headers):
    _post_evento(
        client, model_headers, "YOLO-T-1",
        nivel_agua_cm=44.0, upz="UPZ 74 Engativá", barrio="Jaboque",
    )
    _post_evento(
        client, model_headers, "YOLO-T-2",
        clase="basura", clase_modelo="tapada", estado="BASURA", nivel_agua_cm=0,
        cobertura_basura_pct=65.0, upz="UPZ 26 Las Ferias", barrio="Bonanza",
        localizacion_x=62, localizacion_y=45,
    )

    resp = client.get("/api/zones")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    upzs = {z["nombre"] for z in body["items"]}
    assert "UPZ 74 Engativá" in upzs
    assert "UPZ 26 Las Ferias" in upzs
    # Ordenado por riesgo: el evento con 44 cm de agua va primero
    assert body["items"][0]["nombre"] == "UPZ 74 Engativá"


def test_critical_points(client, model_headers):
    _post_evento(client, model_headers, "YOLO-T-3", nivel_agua_cm=46.0)
    _post_evento(
        client, model_headers, "YOLO-T-4",
        clase="limpia", clase_modelo="limpia", estado="LIMPIA", nivel_agua_cm=0,
    )
    resp = client.get("/api/zones/critical", params={"min_risk": 40})
    assert resp.status_code == 200
    puntos = resp.json()
    ids = {p["punto_id"] for p in puntos}
    assert "YOLO-T-3" in ids
    assert "YOLO-T-4" not in ids  # la clase limpia no es punto crítico


def test_upz_catalogo(client):
    resp = client.get("/api/zones/upz")
    assert resp.status_code == 200
    assert len(resp.json()) == 9
