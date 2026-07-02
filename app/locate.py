"""Backend alternativo de objetos: NVIDIA LocateAnything-3B via MLX (local).

Ativado com OBJECT_BACKEND=locate. Mesmo contrato do ObjectEngine (start,
set_classes, get_classes, label, detect), então o resto do app não muda.

É um VLM de 3B parâmetros: espere segundos por inferência (as caixas atualizam
devagar; o vídeo continua fluido). Licença NVIDIA apenas pesquisa/não-comercial
— serve para demo, não para produto.
"""
import re
import threading

import cv2

from .objects import DEFAULT_VOCAB, EXTENDED_VOCAB

MODEL_ID = "mlx-community/LocateAnything-3B-8bit"
INFER_WIDTH = 512  # reduz a imagem para acelerar o VLM

# vocabulário enxuto por padrão: cada classe custa tokens de saída (= segundos)
DEFAULT_LOCATE_CLASSES = [
    "baseball cap", "beret", "bottle", "smartphone", "laptop",
    "mug", "book", "glasses", "headphones", "wallet",
]

# saída do modelo: <ref>rótulo</ref><box><x1><y1><x2><y2></box>...
# com coordenadas normalizadas em 0-1000
_BOX_RE = re.compile(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>")
_REF_BOX_RE = re.compile(
    r"<ref>([^<]+)</ref>\s*((?:<box><\d+><\d+><\d+><\d+></box>\s*)+)"
)


class LocateEngine:
    # inferência leva ~15-20s; regras de "objeto ausente" precisam de janela maior
    # que o intervalo entre detecções para não disparar falso
    min_absence_window = 60.0

    def __init__(self, conf: float = 0.0):
        self.conf = conf  # o modelo não expõe confiança; mantido pela interface
        self._lock = threading.Lock()
        self._classes: list[str] = []
        self._labels: dict[str, str] = dict(EXTENDED_VOCAB)
        self._model = None
        self._processor = None
        self._config = None

    def start(self):
        from mlx_vlm import load
        from mlx_vlm.utils import load_config

        self._model, self._processor = load(MODEL_ID, trust_remote_code=True)
        self._config = load_config(MODEL_ID, trust_remote_code=True)
        self.set_classes(DEFAULT_LOCATE_CLASSES)

    def set_classes(self, classes: list[str]) -> None:
        classes = [c.strip().lower() for c in classes if c.strip()]
        if not classes:
            classes = list(DEFAULT_LOCATE_CLASSES)
        with self._lock:
            self._classes = classes

    def get_classes(self) -> list[str]:
        with self._lock:
            return list(self._classes)

    def set_labels(self, labels: dict[str, str]) -> None:
        self._labels.update({k.lower(): v for k, v in labels.items() if v})

    def label(self, cls: str) -> str:
        return self._labels.get(cls, cls)

    def detect(self, frame_bgr) -> list[dict]:
        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from PIL import Image

        height, width = frame_bgr.shape[:2]
        scale = INFER_WIDTH / width if width > INFER_WIDTH else 1.0
        small = cv2.resize(frame_bgr, None, fx=scale, fy=scale) if scale < 1.0 else frame_bgr
        image = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))

        prompt = (
            "Locate all the instances that matches the following description: "
            + ". ".join(self.get_classes()) + "."
        )
        formatted = apply_chat_template(self._processor, self._config, prompt, num_images=1)
        result = generate(
            self._model, self._processor, formatted, image,
            max_tokens=384, temperature=0.0, verbose=False,
        )
        text = result.text if hasattr(result, "text") else str(result)
        return self._parse(text, width, height)

    def _parse(self, text: str, width: int, height: int) -> list[dict]:
        detections = []
        known = {c.lower(): c for c in self.get_classes()}
        for match in _REF_BOX_RE.finditer(text):
            raw_label = match.group(1).strip().strip(".,:").lower()
            cls = known.get(raw_label, raw_label)
            for box in _BOX_RE.finditer(match.group(2)):
                x1, y1, x2, y2 = (int(v) for v in box.groups())
                detections.append(
                    {
                        "cls": cls,
                        "label": self.label(cls),
                        "conf": 0.99,  # modelo não expõe score por caixa
                        "bbox": [
                            int(x1 / 1000 * width),
                            int(y1 / 1000 * height),
                            int(x2 / 1000 * width),
                            int(y2 / 1000 * height),
                        ],
                    }
                )
        return detections
