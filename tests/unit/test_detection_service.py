"""Tests unitarios del servicio de detecciones (reglas de priorización)."""

from rally.models.detection import Detection
from rally.services.detection_service import DetectionService


def make_service() -> DetectionService:
    return DetectionService(detections=None, zones=None)  # reglas puras, sin repos


def make_det(**kwargs) -> Detection:
    base = dict(
        evento_id="DET-TEST-1",
        dispositivo_id="camara_remote_01",
        clase="agua",
        nivel_agua_cm=0,
        cobertura_basura_pct=0,
    )
    base.update(kwargs)
    return Detection(**base)


def test_severidad_critica():
    det = make_det(nivel_agua_cm=45)
    assert det.severity == "critico"


def test_severidad_alta():
    det = make_det(nivel_agua_cm=30)
    assert det.severity == "alto"


def test_severidad_por_basura():
    det = make_det(cobertura_basura_pct=55)
    assert det.severity == "medio"


def test_infer_clog_por_drenaje_lento():
    svc = make_service()
    det = make_det(nivel_agua_cm=12, drena_lento=True, lluvia_mm_h=5)
    assert svc.infer_clog(det) is True


def test_infer_clog_por_lluvia_y_agua():
    svc = make_service()
    det = make_det(nivel_agua_cm=15, lluvia_mm_h=20)
    assert svc.infer_clog(det) is True


def test_sin_clog_sin_lluvia():
    svc = make_service()
    det = make_det(nivel_agua_cm=4, lluvia_mm_h=0)
    assert svc.infer_clog(det) is False


def test_risk_score_rango():
    svc = make_service()
    det = make_det(nivel_agua_cm=50, cobertura_basura_pct=100, lluvia_mm_h=40)
    score = svc.risk_score(det, repeticion_30d=10, lluvia_prevista_mm=40)
    assert 0 <= score <= 100
    assert score > 80


def test_risk_score_bajo():
    svc = make_service()
    det = make_det(nivel_agua_cm=2, cobertura_basura_pct=5)
    score = svc.risk_score(det, repeticion_30d=0, lluvia_prevista_mm=0)
    assert score < 25
