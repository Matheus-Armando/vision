"""VisionFlow MVP — FastAPI: páginas, MJPEG, SSE e APIs de pessoas/regras.

OBJECT_BACKEND=yolo (padrão) usa YOLO-World; OBJECT_BACKEND=locate usa o
NVIDIA LocateAnything-3B local via MLX (mais lento; licença só pesquisa).
"""
import asyncio
import json
import os
import re
import shutil
import threading
import unicodedata
import uuid
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import store
from .camera import CameraWorker
from .events import EventBus
from .faces import FaceEngine
from .objects import DEFAULT_VOCAB, EXTENDED_VOCAB, ObjectEngine
from .rules import CONDITION_LABELS, RuleEngine, default_rules

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="VisionFlow MVP")

bus = EventBus()
db = store.load()
if not db["rules"]:
    db["rules"] = default_rules()
    store.save(db)

OBJECT_BACKEND = os.environ.get("OBJECT_BACKEND", "yolo").lower()

faces = FaceEngine(threshold=db["settings"]["face_threshold"])
if OBJECT_BACKEND == "locate":
    from .locate import LocateEngine

    objects = LocateEngine()
else:
    objects = ObjectEngine(conf=db["settings"]["object_conf"])
rules = RuleEngine(bus, objects)
rules.load(db["rules"])
camera = CameraWorker(faces, objects, rules, bus)

ready = {"faces": False, "objects": False}


def _boot():
    bus.emit("system", "Carregando modelos de IA...", cooldown=0)
    faces.start()
    faces.load_people(db["people"])
    ready["faces"] = True
    bus.emit("system", "Reconhecimento facial pronto", cooldown=0)
    objects.start()
    objects.set_labels(db["settings"].get("object_labels", {}))
    custom = db["settings"].get("object_classes")
    if custom:
        objects.set_classes(custom)
    ready["objects"] = True
    backend = "LocateAnything-3B" if OBJECT_BACKEND == "locate" else "YOLO-World"
    bus.emit("system", f"Detecção de objetos pronta ({backend})", cooldown=0)
    camera.start()


@app.on_event("startup")
def startup():
    threading.Thread(target=_boot, daemon=True).start()


# ---------- páginas ----------
@app.get("/")
def index():
    return FileResponse(STATIC / "ambientes.html")


@app.get("/painel")
def painel_page():
    return FileResponse(STATIC / "painel.html")


@app.get("/pessoas")
def pessoas_page():
    return FileResponse(STATIC / "pessoas.html")


@app.get("/regras")
def regras_page():
    return FileResponse(STATIC / "regras.html")


@app.get("/objetos")
def objetos_page():
    return FileResponse(STATIC / "objetos.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------- vídeo e eventos ----------
@app.get("/video_feed")
async def video_feed():
    async def gen():
        while True:
            jpeg = camera.latest_jpeg()
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            await asyncio.sleep(0.04)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/events")
async def events():
    async def gen():
        last_id = 0
        while True:
            snap = bus.snapshot(after_id=last_id)
            if snap["events"]:
                last_id = snap["events"][-1]["id"]
            yield f"data: {json.dumps(snap, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/detections")
def detections():
    return camera.latest_detections()


@app.get("/api/stats")
def stats():
    return bus.stats()


@app.get("/api/snapshot")
def snapshot():
    """Frame cru da câmera (sem caixas desenhadas) — usado na captura de fotos."""
    frame = camera.latest_raw()
    if frame is None:
        raise HTTPException(503, "Câmera ainda não está ao vivo")
    ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise HTTPException(500, "Falha ao codificar o frame")
    return Response(content=jpeg.tobytes(), media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.get("/api/status")
def status():
    return {
        "faces_ready": ready["faces"],
        "objects_ready": ready["objects"],
        "camera": camera.status,
        "fps": camera.fps,
        "people": len(db["people"]),
        "rules": len(db["rules"]),
    }


# ---------- pessoas ----------
def _slugify(name: str) -> str:
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def _person_public(p: dict) -> dict:
    return {"id": p["id"], "name": p["name"], "photos": len(p["embeddings"])}


@app.get("/api/people")
def list_people():
    return [_person_public(p) for p in db["people"]]


@app.post("/api/people")
async def create_person(payload: dict):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Nome obrigatório")
    person_id = _slugify(name)
    if any(p["id"] == person_id for p in db["people"]):
        raise HTTPException(400, "Pessoa já cadastrada com esse nome")
    person = {"id": person_id, "name": name, "embeddings": []}
    db["people"].append(person)
    store.save(db)
    return _person_public(person)


def _find_person(person_id: str) -> dict:
    for p in db["people"]:
        if p["id"] == person_id:
            return p
    raise HTTPException(404, "Pessoa não encontrada")


def _enroll_image(person: dict, image_bgr) -> bool:
    """Extrai o embedding de uma foto e salva ('treinamento')."""
    if not ready["faces"]:
        raise HTTPException(503, "Modelo facial ainda carregando")
    emb = faces.extract(image_bgr)
    if emb is None:
        return False
    person["embeddings"].append([float(v) for v in emb])
    n = len(person["embeddings"])
    cv2.imwrite(str(store.person_dir(person["id"]) / f"{n}.jpg"), image_bgr)
    return True


@app.post("/api/people/{person_id}/photos")
async def upload_photos(person_id: str, files: list[UploadFile]):
    person = _find_person(person_id)
    processed, skipped = 0, 0
    for file in files:
        data = np.frombuffer(await file.read(), dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if image is not None and _enroll_image(person, image):
            processed += 1
        else:
            skipped += 1
    store.save(db)
    faces.load_people(db["people"])
    bus.emit("system", f"{person['name']}: {processed} foto(s) treinada(s)", cooldown=0)
    return {"processed": processed, "skipped": skipped, "total": len(person["embeddings"])}


@app.post("/api/people/{person_id}/capture")
def capture_photo(person_id: str):
    person = _find_person(person_id)
    frame = camera.latest_raw()
    if frame is None:
        raise HTTPException(503, "Câmera ainda não está ao vivo")
    if not _enroll_image(person, frame):
        raise HTTPException(400, "Nenhum rosto encontrado no frame")
    store.save(db)
    faces.load_people(db["people"])
    bus.emit("system", f"{person['name']}: foto capturada e treinada", cooldown=0)
    return {"total": len(person["embeddings"])}


@app.delete("/api/people/{person_id}")
def delete_person(person_id: str):
    person = _find_person(person_id)
    db["people"].remove(person)
    store.save(db)
    faces.load_people(db["people"])
    shutil.rmtree(store.PEOPLE_DIR / person_id, ignore_errors=True)
    return {"ok": True}


@app.get("/api/people/{person_id}/thumb")
def person_thumb(person_id: str):
    d = store.PEOPLE_DIR / person_id
    photos = sorted(d.glob("*.jpg")) if d.exists() else []
    if not photos:
        raise HTTPException(404, "Sem foto")
    return FileResponse(photos[0])


# ---------- regras ----------
@app.get("/api/rules")
def list_rules():
    return db["rules"]


@app.get("/api/rules/meta")
def rules_meta():
    return {
        "conditions": CONDITION_LABELS,
        "people": [{"id": p["id"], "name": p["name"]} for p in db["people"]],
        "objects": [
            {"cls": cls, "label": objects.label(cls)} for cls in objects.get_classes()
        ] if ready["objects"] else [
            {"cls": cls, "label": label} for cls, label in DEFAULT_VOCAB.items()
        ],
    }


@app.post("/api/rules")
async def create_rule(payload: dict):
    rule = _validate_rule(payload)
    db["rules"].append(rule)
    store.save(db)
    rules.load(db["rules"])
    return rule


@app.put("/api/rules/{rule_id}")
async def update_rule(rule_id: str, payload: dict):
    for i, r in enumerate(db["rules"]):
        if r["id"] == rule_id:
            payload["id"] = rule_id
            db["rules"][i] = _validate_rule(payload)
            store.save(db)
            rules.load(db["rules"])
            return db["rules"][i]
    raise HTTPException(404, "Regra não encontrada")


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: str):
    db["rules"] = [r for r in db["rules"] if r["id"] != rule_id]
    store.save(db)
    rules.load(db["rules"])
    return {"ok": True}


def _validate_rule(payload: dict) -> dict:
    condition = payload.get("condition") or {}
    action = payload.get("action") or {}
    if condition.get("type") not in CONDITION_LABELS:
        raise HTTPException(400, "Condição inválida")
    if action.get("type") not in ("banner_green", "banner_red"):
        raise HTTPException(400, "Ação inválida")
    if condition["type"] in ("object_detected", "person_with_object",
                             "person_without_object", "object_absent"):
        if not condition.get("object"):
            raise HTTPException(400, "Escolha o objeto da condição")
    trigger = payload.get("trigger") or {}
    mode = trigger.get("mode", "interval")
    if mode not in ("once", "interval"):
        raise HTTPException(400, "Modo de disparo inválido")
    return {
        "id": payload.get("id") or uuid.uuid4().hex[:8],
        "name": (payload.get("name") or "Regra").strip(),
        "enabled": bool(payload.get("enabled", True)),
        "condition": condition,
        "action": {
            "type": action["type"],
            "text": (action.get("text") or "").strip() or payload.get("name", "Regra"),
            "sound": bool(action.get("sound", False)),
        },
        "trigger": {
            "mode": mode,
            "seconds": max(2.0, float(trigger.get("seconds") or 10)),
        },
    }


# ---------- objetos (vocabulário gerenciável) ----------
def _current_classes() -> list[str]:
    if ready["objects"]:
        return objects.get_classes()
    return db["settings"].get("object_classes") or list(DEFAULT_VOCAB.keys())


@app.get("/api/objects")
def list_objects():
    return {
        "classes": [{"cls": c, "label": objects.label(c)} for c in _current_classes()],
        "conf": db["settings"]["object_conf"],
        "is_default": not db["settings"].get("object_classes"),
    }


@app.post("/api/objects")
async def add_object(payload: dict):
    cls = (payload.get("cls") or "").strip().lower()
    if not cls or not re.fullmatch(r"[a-z0-9 \-]+", cls):
        raise HTTPException(400, "Informe o termo em inglês (letras, números, espaços)")
    label = (payload.get("label") or "").strip()
    classes = _current_classes()
    if cls in classes:
        raise HTTPException(400, "Esse objeto já está no vocabulário")
    classes.append(cls)
    db["settings"]["object_classes"] = classes
    if label:
        db["settings"].setdefault("object_labels", {})[cls] = label
        objects.set_labels({cls: label})
    store.save(db)
    if ready["objects"]:
        objects.set_classes(classes)
    return {"cls": cls, "label": objects.label(cls)}


@app.delete("/api/objects/{cls}")
def remove_object(cls: str):
    classes = [c for c in _current_classes() if c != cls.lower()]
    db["settings"]["object_classes"] = classes
    store.save(db)
    if ready["objects"]:
        objects.set_classes(classes)
    return {"ok": True}


@app.post("/api/objects/reset")
def reset_objects():
    db["settings"]["object_classes"] = []
    store.save(db)
    if ready["objects"]:
        objects.set_classes([])  # vazio = volta ao vocabulário padrão
    return {"ok": True}


@app.post("/api/objects/extended")
def extended_objects():
    """Modo descoberta: carrega o vocabulário amplo (~130 objetos comuns)."""
    classes = list(EXTENDED_VOCAB.keys())
    db["settings"]["object_classes"] = classes
    store.save(db)
    objects.set_labels(EXTENDED_VOCAB)
    if ready["objects"]:
        objects.set_classes(classes)
    return {"count": len(classes)}


@app.post("/api/objects/conf")
async def set_object_conf(payload: dict):
    conf = min(0.9, max(0.1, float(payload.get("conf") or 0.45)))
    db["settings"]["object_conf"] = conf
    store.save(db)
    objects.conf = conf
    return {"conf": conf}


# ---------- configurações (campo avançado da tela Ao Vivo) ----------
@app.post("/api/settings/classes")
async def set_classes(payload: dict):
    classes = [c.strip() for c in (payload.get("classes") or "").split(",") if c.strip()]
    db["settings"]["object_classes"] = classes
    store.save(db)
    if ready["objects"]:
        objects.set_classes(classes)
    return {"classes": objects.get_classes() if ready["objects"] else classes}
