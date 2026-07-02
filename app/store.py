"""Persistência simples em JSON (pessoas, regras, configurações)."""
import json
import threading
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PEOPLE_DIR = DATA_DIR / "people"
DB_PATH = DATA_DIR / "db.json"

_lock = threading.Lock()

DEFAULT_DB = {
    "people": [],
    "rules": [],
    "settings": {
        "face_threshold": 0.40,
        "object_conf": 0.45,
        "object_classes": [],  # vazio = vocabulário padrão (objects.DEFAULT_VOCAB)
        "object_labels": {},   # rótulos customizados: termo em inglês -> português
    },
}


def load() -> dict:
    with _lock:
        if not DB_PATH.exists():
            return json.loads(json.dumps(DEFAULT_DB))
        db = json.loads(DB_PATH.read_text())
        for key, value in DEFAULT_DB.items():
            db.setdefault(key, json.loads(json.dumps(value)))
        for key, value in DEFAULT_DB["settings"].items():
            db["settings"].setdefault(key, value)
        return db


def save(db: dict) -> None:
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = DB_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2))
        tmp.replace(DB_PATH)


def person_dir(person_id: str) -> Path:
    d = PEOPLE_DIR / person_id
    d.mkdir(parents=True, exist_ok=True)
    return d
