"""Constantes globales de SAPO."""

APP_NAME = "SAPO"
LOCALIDAD = "Engativá"
LOCALIDAD_CODIGO = "10"

# Límite de dispositivos IoT registrados (ver firewall en core/security.py)
MAX_CAMERAS = 200

# Umbrales de nivel de agua en calzada / sumidero (cm) -> severidad
SEVERITY_LEVE_MAX_CM = 10.0
SEVERITY_MEDIO_MAX_CM = 20.0
SEVERITY_ALTO_MAX_CM = 40.0

# Umbral de drenaje lento (s): si el agua no baja en este tiempo se infiere taponamiento
SLOW_DRAIN_SECONDS = 180.0

# Cobertura de basura en sumidero (%) que marca prioridad alta
TRASH_COVER_HIGH_PCT = 40.0

# Horas de pronóstico de lluvia que se cruzan para priorizar
RAIN_FORECAST_HOURS = 6

# Peso de cada factor en el score de riesgo 0-100 (services/zone_service.py)
RISK_WEIGHTS = {
    "nivel_agua": 0.40,
    "basura": 0.25,
    "repeticion": 0.20,
    "lluvia": 0.15,
}

# UPZ de la Localidad 10 (piloto exclusivo)
UPZ_ENGATIVA = [
    {"id": "upz74", "codigo": "74", "nombre": "Engativá"},
    {"id": "upz73", "codigo": "73", "nombre": "Garcés Navas"},
    {"id": "upz31", "codigo": "31", "nombre": "Santa Cecilia"},
    {"id": "upz72", "codigo": "72", "nombre": "Bolivia"},
    {"id": "upz116", "codigo": "116", "nombre": "Álamos"},
    {"id": "upz30", "codigo": "30", "nombre": "Boyacá Real"},
    {"id": "upz29", "codigo": "29", "nombre": "Minuto de Dios"},
    {"id": "upz26", "codigo": "26", "nombre": "Las Ferias"},
    {"id": "upz105", "codigo": "105", "nombre": "Jardín Botánico"},
]

# Entidades que reciben alertas del ciclo "Actuar"
ALERT_TARGETS = ["EAAB", "IDIGER", "MOVILIDAD", "ASEO"]

# Tipos de dispositivo del registro de cámaras
DEVICE_TYPES = ("fija", "movil", "camion_succion")
