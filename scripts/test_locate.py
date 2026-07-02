"""Smoke test do backend LocateAnything: 1 frame da câmera (via servidor), tempo e saída."""
import sys
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.locate import LocateEngine  # noqa: E402


def grab_frame() -> np.ndarray:
    """Extrai um JPEG do stream MJPEG do servidor (evita disputar a câmera)."""
    with urllib.request.urlopen("http://127.0.0.1:8000/video_feed", timeout=5) as stream:
        buffer = b""
        while True:
            buffer += stream.read(4096)
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9", start)
            if start != -1 and end != -1:
                jpeg = buffer[start:end + 2]
                return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)


frame = grab_frame()
print(f"frame: {frame.shape[1]}x{frame.shape[0]}")

engine = LocateEngine()
t = time.time()
engine.start()
print(f"carregou em {time.time() - t:.1f}s")

for i in range(2):
    t = time.time()
    dets = engine.detect(frame)
    print(f"inferência {i + 1}: {time.time() - t:.1f}s — {len(dets)} detecções")
    for d in dets:
        print(f"  - {d['label']} ({d['cls']}) bbox={d['bbox']}")
