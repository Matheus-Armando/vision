"""Captura da webcam + inferência em threads separadas.

A thread de captura mantém o vídeo fluido (lê, desenha as últimas detecções e
codifica JPEG); as threads de inferência (rosto e objetos) processam sempre o
frame mais recente, cada uma no seu ritmo.
"""
import threading
import time

import cv2

DISPLAY_WIDTH = 1280

# paleta DeZoio (BGR): monocromática, rose para alertas
WHITE = (255, 255, 255)
ROSE = (72, 29, 225)      # rose-600 #e11d48
GRAY = (170, 170, 170)
DARK = (18, 18, 18)


class CameraWorker(threading.Thread):
    def __init__(self, faces, objects, rules, bus, camera_index: int = 0):
        super().__init__(daemon=True)
        self._faces = faces
        self._objects = objects
        self._rules = rules
        self._bus = bus
        self._camera_index = camera_index
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._raw = None
        self._face_dets: list[dict] = []
        self._obj_dets: list[dict] = []
        self.status = "iniciando"
        self.fps = 0.0

    # ---- consumido pelas rotas ----
    def latest_jpeg(self) -> bytes | None:
        with self._lock:
            return self._jpeg

    def latest_raw(self):
        """Frame cru mais recente (para captura de foto no cadastro)."""
        with self._lock:
            return None if self._raw is None else self._raw.copy()

    def latest_detections(self) -> dict:
        """Últimas detecções (para diagnóstico ao vivo)."""
        with self._lock:
            return {"faces": list(self._face_dets), "objects": list(self._obj_dets)}

    # ---- loops ----
    def run(self):
        cap = cv2.VideoCapture(self._camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if not cap.isOpened():
            self.status = "erro: câmera indisponível"
            self._bus.emit("system", "Câmera indisponível — verifique a permissão", cooldown=0)
            return
        self.status = "ao vivo"

        threading.Thread(target=self._face_loop, daemon=True).start()
        threading.Thread(target=self._object_loop, daemon=True).start()

        frames, fps_t = 0, time.time()
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            if frame.shape[1] > DISPLAY_WIDTH:
                scale = DISPLAY_WIDTH / frame.shape[1]
                frame = cv2.resize(frame, None, fx=scale, fy=scale)

            with self._lock:
                self._raw = frame
                face_dets, obj_dets = self._face_dets, self._obj_dets

            self._rules.evaluate(face_dets, obj_dets)

            annotated = self._draw(frame.copy(), face_dets, obj_dets)
            ok, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ok:
                with self._lock:
                    self._jpeg = jpeg.tobytes()

            frames += 1
            now = time.time()
            if now - fps_t >= 2.0:
                self.fps = round(frames / (now - fps_t), 1)
                frames, fps_t = 0, now

    def _face_loop(self):
        while True:
            frame = self.latest_raw()
            if frame is None:
                time.sleep(0.1)
                continue
            dets = self._faces.analyze(frame)
            with self._lock:
                self._face_dets = dets
            for f in dets:
                if f["name"]:
                    self._bus.emit(
                        "face", f"{f['name']} reconhecido(a)",
                        dedupe_key=f"face:{f['person_id']}", confidence=f["score"],
                    )
                else:
                    self._bus.emit("face", "Pessoa desconhecida detectada",
                                   dedupe_key="face:unknown")

    def _object_loop(self):
        while True:
            frame = self.latest_raw()
            if frame is None or self._objects is None:
                time.sleep(0.1)
                continue
            dets = self._objects.detect(frame)
            with self._lock:
                self._obj_dets = dets
            for o in dets:
                self._bus.emit(
                    "object", f"{o['label'].capitalize()} detectado(a)",
                    dedupe_key=f"object:{o['cls']}", confidence=o["conf"],
                )

    # ---- desenho (linguagem visual DeZoio: caixa fina + cantoneiras + chip) ----
    def _draw(self, frame, face_dets, obj_dets):
        for o in obj_dets:
            x1, y1, x2, y2 = o["bbox"]
            self._det_box(frame, x1, y1, x2, y2, GRAY)
            self._chip(frame, f"{o['label']} {o['conf']:.0%}", x1, y1, DARK, GRAY)
        for f in face_dets:
            x1, y1, x2, y2 = f["bbox"]
            if f["name"]:
                self._det_box(frame, x1, y1, x2, y2, WHITE)
                self._chip(frame, f["name"], x1, y1, WHITE, DARK)
                self._chip(frame, f"conf {f['score']:.0%}", x1, y2 + 18, DARK, WHITE)
            else:
                self._det_box(frame, x1, y1, x2, y2, ROSE)
                self._chip(frame, "DESCONHECIDO", x1, y1, ROSE, WHITE)
        return frame

    @staticmethod
    def _det_box(frame, x1, y1, x2, y2, color, corner=14, thick=2):
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
        for cx, cy, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1),
                               (x1, y2, 1, -1), (x2, y2, -1, -1)):
            cv2.line(frame, (cx, cy), (cx + dx * corner, cy), color, thick)
            cv2.line(frame, (cx, cy), (cx, cy + dy * corner), color, thick)

    @staticmethod
    def _chip(frame, text, x, y, bg, fg):
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        y0 = max(th + 8, y)
        cv2.rectangle(frame, (x, y0 - th - 8), (x + tw + 10, y0 - 2), bg, -1)
        cv2.putText(frame, text, (x + 5, y0 - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, fg, 1, cv2.LINE_AA)
