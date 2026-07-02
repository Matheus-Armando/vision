"""Detecção de objetos open-vocabulary com YOLO-World.

As classes são definidas por texto (em inglês, idioma do modelo) e
exibidas com rótulo em português. Sem treino: basta ajustar o vocabulário.
"""
import threading

# vocabulário padrão: aponte a câmera e ele reconhece, sem digitar nada
DEFAULT_VOCAB = {
    "baseball cap": "boné",
    "beret": "boina",
    "bottle": "garrafa",
    "smartphone": "celular",
    "laptop": "notebook",
    "book": "livro",
    "cup": "xícara",
    "mug": "caneca",
    "cardboard box": "caixa",
    "keyboard": "teclado",
    "computer mouse": "mouse",
    "headphones": "fone de ouvido",
    "glasses": "óculos",
    "wristwatch": "relógio",
    "backpack": "mochila",
    "chair": "cadeira",
    "scissors": "tesoura",
    "pen": "caneta",
    "banana": "banana",
    "apple": "maçã",
    "orange": "laranja",
    "dog": "cachorro",
    "cat": "gato",
    "bird": "pássaro",
    "wrench": "chave inglesa",
    "screwdriver": "chave de fenda",
    "hammer": "martelo",
    "knife": "faca",
    "fork": "garfo",
    "spoon": "colher",
    "remote control": "controle remoto",
    "leather wallet": "carteira",
    "key": "chave",
    "id card": "crachá",
    "document": "documento",
    "face mask": "máscara",
}


# vocabulário amplo ("modo descoberta"): ~130 objetos comuns. Embeddings de
# texto são calculados uma única vez no set_classes, então a velocidade de
# detecção não muda — o custo é um pouco mais de ruído (ajuste na confiança).
EXTENDED_VOCAB = {
    **DEFAULT_VOCAB,
    # pessoas e vestuário
    "person": "pessoa",
    "safety vest": "colete de segurança",
    "hard hat": "capacete de obra",
    "helmet": "capacete",
    "jacket": "casaco",
    "t-shirt": "camiseta",
    "shoe": "sapato",
    "boot": "bota",
    "glove": "luva",
    "tie": "gravata",
    "hat": "chapéu",
    "scarf": "cachecol",
    "handbag": "bolsa",
    "suitcase": "mala",
    "umbrella": "guarda-chuva",
    # escritório e eletrônicos
    "monitor": "monitor",
    "television": "televisão",
    "tablet": "tablet",
    "printer": "impressora",
    "camera": "câmera",
    "microphone": "microfone",
    "speaker": "caixa de som",
    "charger": "carregador",
    "cable": "cabo",
    "power strip": "filtro de linha",
    "lamp": "luminária",
    "desk": "mesa de trabalho",
    "office chair": "cadeira de escritório",
    "whiteboard": "quadro branco",
    "notebook paper": "caderno",
    "pencil": "lápis",
    "marker": "marcador",
    "stapler": "grampeador",
    "calculator": "calculadora",
    "envelope": "envelope",
    "folder": "pasta de documentos",
    "clipboard": "prancheta",
    "badge": "crachá",
    # casa e cozinha
    "table": "mesa",
    "sofa": "sofá",
    "bed": "cama",
    "pillow": "almofada",
    "blanket": "cobertor",
    "mirror": "espelho",
    "clock": "relógio de parede",
    "vase": "vaso",
    "plant": "planta",
    "flower": "flor",
    "picture frame": "porta-retrato",
    "candle": "vela",
    "plate": "prato",
    "bowl": "tigela",
    "glass": "copo",
    "wine glass": "taça",
    "pan": "panela",
    "pot": "panela grande",
    "kettle": "chaleira",
    "microwave": "micro-ondas",
    "refrigerator": "geladeira",
    "toaster": "torradeira",
    "blender": "liquidificador",
    "cutting board": "tábua de corte",
    "towel": "toalha",
    "broom": "vassoura",
    "bucket": "balde",
    "trash can": "lixeira",
    # comida
    "sandwich": "sanduíche",
    "pizza": "pizza",
    "cake": "bolo",
    "bread": "pão",
    "egg": "ovo",
    "tomato": "tomate",
    "carrot": "cenoura",
    "lettuce": "alface",
    "grapes": "uvas",
    "strawberry": "morango",
    "watermelon": "melancia",
    "pineapple": "abacaxi",
    "lemon": "limão",
    "coffee cup": "copo de café",
    "can": "lata",
    "jar": "pote",
    # ferramentas e indústria
    "drill": "furadeira",
    "saw": "serrote",
    "pliers": "alicate",
    "tape measure": "trena",
    "ladder": "escada",
    "toolbox": "caixa de ferramentas",
    "fire extinguisher": "extintor",
    "traffic cone": "cone de sinalização",
    "pallet": "pallet",
    "barrel": "barril",
    "gas cylinder": "cilindro de gás",
    "pipe": "cano",
    "rope": "corda",
    "chain": "corrente",
    "padlock": "cadeado",
    "battery": "bateria",
    "tire": "pneu",
    # veículos
    "car": "carro",
    "truck": "caminhão",
    "motorcycle": "moto",
    "bicycle": "bicicleta",
    "bus": "ônibus",
    "forklift": "empilhadeira",
    # animais
    "horse": "cavalo",
    "cow": "vaca",
    "sheep": "ovelha",
    "chicken": "galinha",
    "fish": "peixe",
    "rabbit": "coelho",
    # diversos
    "ball": "bola",
    "toy": "brinquedo",
    "game controller": "controle de videogame",
    "guitar": "violão",
    "skateboard": "skate",
    "money": "dinheiro",
    "coin": "moeda",
    "credit card": "cartão",
    "cigarette": "cigarro",
    "syringe": "seringa",
    "pill bottle": "frasco de remédio",
    "first aid kit": "kit de primeiros socorros",
}


class ObjectEngine:
    def __init__(self, conf: float = 0.45):
        self.conf = conf
        self._lock = threading.Lock()
        self._model = None
        self._classes: list[str] = []
        # rótulos do vocabulário amplo cobrem também o padrão (superconjunto)
        self._labels: dict[str, str] = dict(EXTENDED_VOCAB)

    def start(self):
        import torch
        from ultralytics import YOLOWorld

        self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._model = YOLOWorld("yolov8l-worldv2.pt")
        self.set_classes(list(DEFAULT_VOCAB.keys()))

    def set_classes(self, classes: list[str]) -> None:
        classes = [c.strip().lower() for c in classes if c.strip()]
        if not classes:
            classes = list(DEFAULT_VOCAB.keys())
        with self._lock:
            try:
                self._model.set_classes(classes)
            except RuntimeError:
                # com o modelo já no MPS, o encoder de texto fica com pesos e
                # entrada em dispositivos diferentes; realinha na CPU e repete
                # (o próximo predict devolve o modelo ao MPS)
                self._model.to("cpu")
                self._model.set_classes(classes)
            self._classes = classes

    def get_classes(self) -> list[str]:
        with self._lock:
            return list(self._classes)

    def set_labels(self, labels: dict[str, str]) -> None:
        """Mescla rótulos customizados (en -> pt) sobre os padrão."""
        self._labels.update({k.lower(): v for k, v in labels.items() if v})

    def label(self, cls: str) -> str:
        return self._labels.get(cls, cls)

    def detect(self, frame_bgr) -> list[dict]:
        """Retorna [{cls, label, conf, bbox}] para o frame."""
        with self._lock:
            results = self._model.predict(
                frame_bgr, conf=self.conf, device=self._device, verbose=False
            )
        detections = []
        for result in results:
            names = result.names
            for box in result.boxes:
                cls = names[int(box.cls)]
                detections.append(
                    {
                        "cls": cls,
                        "label": self.label(cls),
                        "conf": round(float(box.conf), 3),
                        "bbox": [int(v) for v in box.xyxy[0]],
                    }
                )
        return detections
