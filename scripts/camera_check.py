"""Dispara o pedido de permissão de câmera do macOS e valida a captura."""
import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("FALHOU: câmera não autorizada ou indisponível.")
    print("Vá em Ajustes do Sistema > Privacidade e Segurança > Câmera")
    print("e habilite o app do terminal (Terminal/iTerm/Claude).")
else:
    ok, frame = cap.read()
    print(f"OK: câmera capturando ({frame.shape[1]}x{frame.shape[0]})" if ok else "Abriu mas não leu frame")
cap.release()
