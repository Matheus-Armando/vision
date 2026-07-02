"""Baixa e valida os modelos (rodar com internet, antes do dia da demo)."""
import numpy as np

print("== InsightFace buffalo_l ==")
from insightface.app import FaceAnalysis

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"],
    allowed_modules=["detection", "recognition"],
)
face_app.prepare(ctx_id=-1, det_size=(640, 640))
face_app.get(np.zeros((480, 640, 3), dtype=np.uint8))
print("OK: buffalo_l carregado e inferência executada")

print("== YOLO-World ==")
from ultralytics import YOLOWorld

model = YOLOWorld("yolov8l-worldv2.pt")
model.set_classes(["bottle", "smartphone", "baseball cap"])
model.predict(np.zeros((480, 640, 3), dtype=np.uint8), verbose=False)
print("OK: YOLO-World carregado, set_classes e inferência executados")
print("Modelos prontos. O LocateAnything (opcional, OBJECT_BACKEND=locate) baixa")
print("sozinho na primeira execução — requer requirements-locate.txt (só macOS).")
