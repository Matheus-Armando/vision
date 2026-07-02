"""Reconhecimento facial com InsightFace (buffalo_l: RetinaFace + ArcFace).

"Treinar" uma pessoa = extrair o embedding de cada foto e guardar.
Reconhecer = similaridade de cosseno entre o embedding do rosto ao vivo
e os embeddings cadastrados.
"""
import threading

import numpy as np


class FaceEngine:
    def __init__(self, threshold: float = 0.40):
        self.threshold = threshold
        self._lock = threading.Lock()
        # matriz N x 512 com todos os embeddings cadastrados e, em paralelo,
        # o dono de cada linha — permite match vetorizado num único produto
        self._embeddings = np.zeros((0, 512), dtype=np.float32)
        self._owners: list[dict] = []  # {"id", "name"} por linha
        self._app = None

    def start(self):
        from insightface.app import FaceAnalysis

        self._app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        self._app.prepare(ctx_id=-1, det_size=(640, 640))

    def load_people(self, people: list[dict]) -> None:
        rows, owners = [], []
        for person in people:
            for emb in person.get("embeddings", []):
                rows.append(np.asarray(emb, dtype=np.float32))
                owners.append({"id": person["id"], "name": person["name"]})
        with self._lock:
            self._embeddings = (
                np.stack(rows) if rows else np.zeros((0, 512), dtype=np.float32)
            )
            self._owners = owners

    def extract(self, image_bgr) -> np.ndarray | None:
        """Embedding do maior rosto da imagem (para cadastro)."""
        faces = self._app.get(image_bgr)
        if not faces:
            return None
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.normed_embedding.astype(np.float32)

    def analyze(self, frame_bgr) -> list[dict]:
        """Detecta rostos no frame e identifica cada um.

        Retorna [{bbox, name, person_id, score}] — name=None para desconhecido.
        """
        results = []
        for face in self._app.get(frame_bgr):
            emb = face.normed_embedding.astype(np.float32)
            name, person_id, score = self._match(emb)
            results.append(
                {
                    "bbox": [int(v) for v in face.bbox],
                    "name": name,
                    "person_id": person_id,
                    "score": round(float(score), 3),
                }
            )
        return results

    def _match(self, embedding: np.ndarray):
        with self._lock:
            if len(self._owners) == 0:
                return None, None, 0.0
            sims = self._embeddings @ embedding  # embeddings já normalizados
            idx = int(np.argmax(sims))
            best = float(sims[idx])
            if best >= self.threshold:
                owner = self._owners[idx]
                return owner["name"], owner["id"], best
            return None, None, best
