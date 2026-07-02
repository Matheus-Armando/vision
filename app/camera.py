"""Captura da webcam + inferência em threads separadas.

A thread de captura mantém o vídeo fluido (lê, desenha as últimas detecções e
codifica JPEG); as threads de inferência (rosto e objetos) processam sempre o
frame mais recente, cada uma no seu ritmo.
"""
import threading
import time

import cv2

DISPLAY_WIDTH = 1280

GREEN, RED, BLUE, WHITE = (80, 200, 120), (80, 80, 235), (235, 160, 80), (255, 255, 255)


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

    # ---- desenho ----
    def _draw(self, frame, face_dets, obj_dets):
        for o in obj_dets:
            x1, y1, x2, y2 = o["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), BLUE, 2)
            self._label(frame, f"{o['label']} {o['conf']:.0%}", x1, y1, BLUE)
        for f in face_dets:
            x1, y1, x2, y2 = f["bbox"]
            color = GREEN if f["name"] else RED
            text = f"{f['name']} {f['score']:.0%}" if f["name"] else "Desconhecido"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            self._label(frame, text, x1, y1, color)
        return frame

    @staticmethod
    def _label(frame, text, x, y, color):
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x, y - th - 10), (x + tw + 8, y), color, -1)
        cv2.putText(frame, text, (x + 4, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)
