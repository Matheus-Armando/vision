"""Prova de conceito: webcam + reconhecimento facial numa janela OpenCV.

Uso: python scripts/test_pipeline.py [foto_de_referencia.jpg] [nome]
Sem argumentos, apenas detecta rostos (todos como 'desconhecido').
Tecla Q encerra.
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.faces import FaceEngine  # noqa: E402

engine = FaceEngine()
print("Carregando buffalo_l...")
engine.start()

if len(sys.argv) > 1:
    ref_path, name = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Referência"
    image = cv2.imread(ref_path)
    emb = engine.extract(image)
    if emb is None:
        sys.exit(f"Nenhum rosto encontrado em {ref_path}")
    engine.load_people([{"id": "ref", "name": name, "embeddings": [emb.tolist()]}])
    print(f"Referência cadastrada: {name}")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    sys.exit("Câmera indisponível — verifique a permissão do Terminal em "
             "Ajustes > Privacidade e Segurança > Câmera")

print("Câmera aberta — janela deve abrir; Q para sair")
while True:
    ok, frame = cap.read()
    if not ok:
        continue
    for f in engine.analyze(frame):
        x1, y1, x2, y2 = f["bbox"]
        color = (80, 200, 120) if f["name"] else (80, 80, 235)
        text = f"{f['name']} {f['score']:.0%}" if f["name"] else "Desconhecido"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, text, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.imshow("VisionFlow PoC", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
