import time                          # reloj para el modo cámara
import threading                     # para que el sonido no congele el video
import os                            # variables de entorno del puente SAPO
from collections import deque, Counter   # ventanas deslizantes y conteo de votos
from pathlib import Path             # rutas cómodas en Windows
import cv2                           # OpenCV: captura y dibujo
import torch                         # para detectar la GPU
from ultralytics import YOLO         # YOLOv8
try:
    from sapo_json import SapoEmisor   # puente hacia la web visual de SAPO
except ImportError:
    SapoEmisor = None                  # el monitor sigue funcionando solo
try:
    import winsound                  # sonido nativo de Windows
except ImportError:
    winsound = None                  # en otros sistemas no hay sonido (no se rompe nada)

# ======================= CONFIGURACION (lo que vas a tocar) =======================
FUENTE = 0                           # 0 = cámara web; o ruta de video: r"C:/Users/sneid/Videos/prueba.mp4"
UMBRAL_DRENAJE_S = 10.0              # segundos para disparar la alerta (cámbialo aquí)
CONF_POR_CLASE = {0: 0.30, 1: 0.35, 2: 0.40}   # confianza mínima: 0 limpia, 1 tapada, 2 con_agua
VENTANA_VOTOS = 15                   # frames que se usan para votar el estado
SHARE_MIN = 0.55                     # fracción mínima de votos para confirmar un estado
VENTANA_AREA = 10                    # frames para suavizar el área del agua
BAJADA_DRENANDO = 0.75               # área < 75 % del pico => DRENANDO
SUBIDA_INUNDADA = 0.90               # área > 90 % del pico => vuelve a INUNDADA
TIMEOUT_SIN_DET_S = 8.0              # si se pierde toda detección tanto tiempo estando inundada, se cierra el episodio
# --- Puente SAPO: JSON para la web (data/live/detecciones.json) y API opcional ---
SAPO_SALIDA_JSON = Path(__file__).resolve().parents[1] / "data" / "live" / "detecciones.json"
SAPO_API = os.environ.get("SAPO_API", "")        # ej. "http://localhost:8000" (vacío = solo archivo)
SAPO_TOKEN = os.environ.get("SAPO_MODEL_TOKEN", "")
SAPO_DISPOSITIVO = os.environ.get("SAPO_DISPOSITIVO", "camara_modelo_01")
MOSTRAR_VIDEO = os.environ.get("SAPO_NO_VENTANA", "") != "1"   # SAPO_NO_VENTANA=1 = sin ventana (headless)
# ==================================================================================

LIMPIA, BASURA, INUNDADA, DRENANDO, SIN_DET = "LIMPIA", "BASURA", "INUNDADA", "DRENANDO", "SIN_DET"  # estados
TEXTO = {LIMPIA: "LIMPIA", BASURA: "CON BASURA (TAPADA)", INUNDADA: "INUNDADA",
         DRENANDO: "DRENANDO", SIN_DET: "SIN DETECCION"}                       # texto en pantalla (sin tildes)
COLOR = {LIMPIA: (0, 200, 0), BASURA: (0, 165, 255), INUNDADA: (255, 120, 0),
         DRENANDO: (255, 200, 0), SIN_DET: (160, 160, 160)}                    # colores BGR por estado
CLASE_A_ESTADO = {0: LIMPIA, 1: BASURA}                                        # clases "normales"
NOMBRES = {0: "limpia", 1: "tapada", 2: "con_agua"}                            # nombres de clase del modelo


def buscar_modelo():
    # Busca el best.pt más reciente dentro de runs/ (así no dependes del nombre exacto de la corrida)
    candidatos = sorted(Path(__file__).parent.glob("runs/**/weights/best.pt"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise FileNotFoundError("No encontré ningún best.pt dentro de la carpeta runs/")
    return candidatos[0]


class Monitor:
    # Máquina de estados: decide el estado confirmado, el cronómetro y la alerta
    def __init__(self):
        self.votos = deque(maxlen=VENTANA_VOTOS)   # etiqueta de cada frame: 0, 1, 2 o -1 (nada)
        self.areas = deque(maxlen=VENTANA_AREA)    # área del agua (fracción del frame) de cada frame
        self.estado = SIN_DET                      # estado confirmado actual
        self.t_inicio = None                       # momento en que empezó la inundación
        self.pico = 0.0                            # área máxima de agua vista en este episodio
        self.alerta = False                        # True si ya se superó el umbral
        self.t_sin_det = None                      # desde cuándo no se detecta nada
        self.ultimo_tiempo = None                  # duración del último episodio terminado
        self.ultimo_con_alerta = False             # si ese episodio superó el umbral

    def _confirmada(self):
        # Devuelve la etiqueta ganadora de la ventana, o None si no hay consenso suficiente
        if len(self.votos) < VENTANA_VOTOS // 2:   # muy pocos frames todavía
            return None
        etiqueta, n = Counter(self.votos).most_common(1)[0]   # etiqueta más votada
        return etiqueta if n / len(self.votos) >= SHARE_MIN else None

    def _cerrar(self, t, nuevo_estado):
        # Termina el episodio de inundación y guarda cuánto duró
        self.ultimo_tiempo = t - self.t_inicio
        self.ultimo_con_alerta = self.alerta
        self.estado, self.t_inicio, self.pico, self.alerta = nuevo_estado, None, 0.0, False

    def transcurrido(self, t):
        # Segundos desde que empezó la inundación (None si no hay inundación)
        return None if self.t_inicio is None else t - self.t_inicio

    def actualizar(self, clase, area_agua, t):
        # clase: etiqueta del frame (0,1,2 o -1); area_agua: fracción del frame; t: tiempo en segundos
        # Devuelve True solo en el instante en que se dispara una alerta nueva
        self.votos.append(clase)
        self.areas.append(area_agua)
        area = sum(self.areas) / len(self.areas)           # área suavizada del agua
        conf = self._confirmada()                           # etiqueta confirmada por votación
        inundando = self.estado in (INUNDADA, DRENANDO)     # ¿hay un episodio en curso?

        if conf != -1:
            self.t_sin_det = None                           # hay detección: reiniciamos el contador de pérdida

        if conf == 2:                                       # ---- agua confirmada ----
            if not inundando:                               # empieza una inundación nueva
                self.estado, self.t_inicio, self.pico, self.alerta = INUNDADA, t, area, False
            elif self.estado == INUNDADA:                   # inundada: seguimos el pico y buscamos bajada
                self.pico = max(self.pico, area)
                if area < self.pico * BAJADA_DRENANDO:
                    self.estado = DRENANDO
            elif area > self.pico * SUBIDA_INUNDADA:        # estaba drenando pero el agua volvió a subir
                self.estado = INUNDADA
        elif conf in CLASE_A_ESTADO:                        # ---- limpia o tapada confirmada ----
            nuevo = CLASE_A_ESTADO[conf]
            if inundando:
                self._cerrar(t, nuevo)                      # el agua se fue: termina el episodio
            else:
                self.estado = nuevo
        elif conf == -1:                                    # ---- no se detecta nada ----
            if inundando:
                if self.t_sin_det is None:
                    self.t_sin_det = t
                elif t - self.t_sin_det > TIMEOUT_SIN_DET_S:
                    self._cerrar(t, SIN_DET)                # demasiado tiempo sin ver nada: cerramos
            else:
                self.estado = SIN_DET

        if self.estado in (INUNDADA, DRENANDO) and not self.alerta:   # ¿se pasó el umbral?
            if t - self.t_inicio > UMBRAL_DRENAJE_S:
                self.alerta = True
                return True                                  # señal: alerta nueva
        return False


def pitido():
    # Dos pitidos en un hilo aparte para no congelar el video
    if winsound:
        threading.Thread(target=lambda: [winsound.Beep(1000, 350), winsound.Beep(1400, 350)], daemon=True).start()


def dibujar(frame, detecciones, monitor, t):
    # Dibuja cajas, panel de estado, cronómetro y banner de alerta sobre el frame
    for (x1, x2, y1, y2, c, conf) in detecciones:            # una caja por detección válida
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
        cv2.putText(frame, f"{NOMBRES[c]} {conf:.2f}", (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    cv2.rectangle(frame, (0, 0), (frame.shape[1], 78), (0, 0, 0), -1)         # franja negra superior
    cv2.putText(frame, f"ESTADO: {TEXTO[monitor.estado]}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLOR[monitor.estado], 2)      # estado actual con su color

    trans = monitor.transcurrido(t)
    if trans is not None:                                                     # hay inundación en curso
        linea = f"CRONOMETRO: {trans:5.1f} s  (limite {UMBRAL_DRENAJE_S:.0f} s)"
    elif monitor.ultimo_tiempo is not None:                                   # ya terminó una inundación
        extra = " - SUPERO EL LIMITE" if monitor.ultimo_con_alerta else ""
        linea = f"ULTIMO DRENAJE: {monitor.ultimo_tiempo:.1f} s{extra}"
    else:
        linea = "CRONOMETRO: -"
    cv2.putText(frame, linea, (10, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if monitor.alerta and int(t * 2) % 2 == 0:                                # banner que parpadea 2 veces por segundo
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, h - 60), (w, h), (0, 0, 255), -1)
        cv2.putText(frame, "ALERTA: DRENAJE LENTO", (15, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)


def main():
    ruta_modelo = buscar_modelo()                         # best.pt más reciente
    gpu = torch.cuda.is_available()                       # ¿hay GPU?
    device, imgsz = (0, 640) if gpu else ("cpu", 512)     # mismo imgsz con el que se entrenó en cada caso
    print(f"Modelo: {ruta_modelo}\nDispositivo: {'GPU' if gpu else 'CPU'}")
    modelo = YOLO(str(ruta_modelo))                       # carga el modelo

    cap = cv2.VideoCapture(FUENTE)                        # abre cámara o video
    if not cap.isOpened():
        print("No se pudo abrir la fuente de video:", FUENTE)
        return
    es_video = isinstance(FUENTE, str)                    # True si es archivo, False si es cámara
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0               # fps del video (30 si no los informa)
    n_frame = 0                                           # contador de frames
    monitor = Monitor()
    ultimo_pitido = 0.0                                   # para repetir el sonido mientras dure la alerta
    conf_min = min(CONF_POR_CLASE.values())               # umbral global bajo; luego filtramos por clase

    # Puente hacia la web: cada cambio de estado se publica como JSON
    emisor = None
    if SapoEmisor is not None:
        emisor = SapoEmisor(
            dispositivo_id=SAPO_DISPOSITIVO,
            salida=SAPO_SALIDA_JSON,
            api_url=SAPO_API,
            token=SAPO_TOKEN,
            modelo=str(ruta_modelo),
        )
        emisor.cargar()                                   # continúa el historial ya publicado
        print(f"JSON de la web: {SAPO_SALIDA_JSON}" + (f" + API {SAPO_API}" if SAPO_API else ""))

    while True:
        ok, frame = cap.read()                            # leemos un frame
        if not ok:                                        # fin del video o cámara desconectada
            break
        t = n_frame / fps if es_video else time.perf_counter()   # tiempo del video o tiempo real
        n_frame += 1

        r = modelo.predict(frame, conf=conf_min, imgsz=imgsz, device=device, verbose=False)[0]  # inferencia
        area_frame = frame.shape[0] * frame.shape[1]      # área total del frame
        detecciones, mejor_clase, mejor_conf, area_agua = [], -1, 0.0, 0.0
        area_mejor = 0.0                                  # área (fracción del frame) de la mejor detección
        for box in r.boxes:                               # recorremos las detecciones
            c, conf = int(box.cls[0]), float(box.conf[0])
            if conf < CONF_POR_CLASE[c]:                  # descartamos las que no pasan el umbral de su clase
                continue
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detecciones.append((x1, x2, y1, y2, c, conf))
            area_caja = (x2 - x1) * (y2 - y1) / area_frame
            if conf > mejor_conf:                         # la de mayor confianza define la etiqueta del frame
                mejor_clase, mejor_conf, area_mejor = c, conf, area_caja
            if c == 2:                                    # área del agua: la caja de agua más grande
                area_agua = max(area_agua, area_caja)

        estado_previo = monitor.estado
        alerta_nueva = monitor.actualizar(mejor_clase, area_agua, t)   # True = alerta nueva
        if emisor is not None and (alerta_nueva or monitor.estado != estado_previo):
            # Se publica el cambio de estado (o la alerta de drenaje lento) como JSON.
            # La clase del evento sigue el estado confirmado del monitor (no el frame).
            clase_modelo = {"INUNDADA": "con_agua", "DRENANDO": "con_agua",
                            "BASURA": "tapada", "LIMPIA": "limpia"}.get(monitor.estado)
            if clase_modelo is None:                      # SIN_DET: se toma lo del frame
                clase_modelo = NOMBRES.get(mejor_clase, "limpia")
            if clase_modelo == "con_agua":
                area_evento = area_agua if area_agua else monitor.pico
            else:
                area_evento = area_mejor
            trans = monitor.transcurrido(t)
            emisor.registrar(emisor.nuevo_evento(
                clase_modelo=clase_modelo,
                confianza=mejor_conf if mejor_conf else 0.5,
                area_frac=area_evento,
                estado=monitor.estado,
                drena_lento=bool(monitor.alerta),
                tiempo_drenaje_s=(trans if trans is not None else monitor.ultimo_tiempo),
            ))
        if alerta_nueva:
            print(f"[ALERTA] Drenaje superó {UMBRAL_DRENAJE_S:.0f} s")
        ahora = time.perf_counter()
        if monitor.alerta and ahora - ultimo_pitido > 3.0:   # sonido cada 3 s mientras siga la alerta
            pitido()
            ultimo_pitido = ahora

        if MOSTRAR_VIDEO:
            dibujar(frame, detecciones, monitor, t)       # pintamos todo sobre el frame
            cv2.imshow("Monitor de alcantarilla (q = salir, r = reiniciar)", frame)
            tecla = cv2.waitKey(1) & 0xFF                 # leemos teclado
            if tecla == ord("q"):
                break
            if tecla == ord("r"):                         # reinicia el estado y el cronómetro
                monitor = Monitor()

    if emisor is not None:
        emisor.guardar()                                  # deja el JSON de la web al día
    cap.release()                                         # libera la cámara o el video
    if MOSTRAR_VIDEO:
        cv2.destroyAllWindows()                           # cierra las ventanas

if __name__ == "__main__":
    main()