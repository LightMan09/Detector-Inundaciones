"""Tests de integración: cámaras y firewall IoT (registro en runtime)."""


def test_registry_empieza_vacio(client):
    resp = client.get("/api/cameras")
    assert resp.status_code == 200
    assert resp.json() == []


def test_register_camera(client):
    payload = {
        "dispositivo_id": "camara_modelo_01",
        "mac": "AA:BB:CC:00:00:99",
        "ip": "186.1.2.3",
        "localizacion_x": 20,
        "localizacion_y": 30,
        "barrio": "Jaboque",
        "upz": "UPZ 74 Engativá",
        "tipo": "fija",
        "ubicacion": "Ronda Humedal Jaboque",
        "fuente": "movilidad",
    }
    resp = client.post("/api/cameras", json=payload)
    assert resp.status_code == 201
    assert resp.json()["dispositivo_id"] == "camara_modelo_01"

    # El firewall debe reflejar el alta sin reiniciar el servicio
    push = client.post(
        "/api/cameras/ingest",
        headers={"X-Device-Id": "camara_modelo_01"},
        json={"dispositivo_id": "camara_modelo_01", "estado": "activa"},
    )
    assert push.status_code == 200
    assert push.json()["firewall"] is True


def test_get_camera_not_found(client):
    resp = client.get("/api/cameras/no_existe")
    assert resp.status_code == 404


def test_firewall_bloquea_desconocido(client):
    resp = client.post(
        "/api/cameras/ingest",
        json={"dispositivo_id": "camara_hacker", "estado": "activa"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "device_not_allowed"
