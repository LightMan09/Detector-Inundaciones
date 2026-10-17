"""Tests de integración: detecciones del modelo, alertas y despacho."""


def test_detections_require_token(client):
    resp = client.post(
        "/api/detections", json={"dispositivo_id": "camara_modelo_01", "detections": []}
    )
    assert resp.status_code == 403


def test_receive_detections(client, model_headers, evento_base):
    evento_base["evento_id"] = "YOLO-TEST-000001"
    critico = dict(evento_base)
    leve = dict(
        evento_base,
        evento_id="YOLO-TEST-000002",
        clase="basura",
        clase_modelo="tapada",
        estado="BASURA",
        nivel_agua_cm=0.0,
        cobertura_basura_pct=15.0,
        upz="UPZ 72 Bolivia",
        barrio="El Cortijo",
    )
    resp = client.post(
        "/api/detections",
        json={"dispositivo_id": "camara_modelo_01", "detections": [critico, leve]},
        headers=model_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recibidas"] == 2
    assert body["criticas"] == 1
    assert body["alertas_generadas"] == 1

    listed = client.get("/api/detections").json()
    ids = [d["evento_id"] for d in listed["items"]]
    assert "YOLO-TEST-000001" in ids
    # El evento viaja con su posición aleatoria sobre el mapa
    det = next(d for d in listed["items"] if d["evento_id"] == "YOLO-TEST-000001")
    assert det["localizacion_x"] == 27.5
    assert det["clase_modelo"] == "con_agua"

    alerts = client.get("/api/alerts").json()
    assert any(
        a["punto_critico_id"] == "YOLO-TEST-000001" or "Quirigua" in a["titulo"]
        for a in alerts
    )


def test_summary(client, model_headers, evento_base):
    client.post(
        "/api/detections",
        json={"dispositivo_id": "camara_modelo_01", "detections": [evento_base]},
        headers=model_headers,
    )
    resp = client.get("/api/detections/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["criticas"] == 1
    assert body["nivel_max_cm"] == 44.0


def test_dispatch_orders(client, model_headers, evento_base):
    evento_base["evento_id"] = "YOLO-TEST-000010"
    evento_base["drena_lento"] = True
    evento_base["tiempo_drenaje_s"] = 520.0
    client.post(
        "/api/detections",
        json={"dispositivo_id": "camara_modelo_01", "detections": [evento_base]},
        headers=model_headers,
    )
    resp = client.post("/api/dispatch")
    assert resp.status_code == 200
    body = resp.json()
    assert body["generadas"] >= 1
    first = body["ordenes"][0]
    assert first["camion_id"].startswith("EAAB")
    assert first["punto_critico_id"] == "YOLO-TEST-000010"
    assert first["ruta"]


def test_create_alert(client):
    resp = client.post(
        "/api/alerts",
        json={
            "titulo": "Alerta manual COE",
            "severidad": "alto",
            "upz": "UPZ 73 Garcés Navas",
            "punto_critico_id": "YOLO-TEST-X",
            "detalle": "Prueba de protocolo",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["alerta_id"].startswith("ALERT-")
    assert "IDIGER" in body["notificados"]
