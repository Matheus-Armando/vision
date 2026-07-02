"""Motor de regras SE → ENTÃO.

Cada regra: {id, name, enabled, condition: {type, ...}, action: {type, text, sound}}.

Condições:
  person_recognized      {person_id|null}          — pessoa (qualquer ou específica) reconhecida
  unknown_person         {}                        — rosto desconhecido na cena
  object_detected        {object}                  — objeto presente na cena
  person_with_object     {person_id|null, object}  — pessoa associada geometricamente ao objeto
  person_without_object  {person_id|null, object}  — pessoa SEM o objeto associado
  object_absent          {object, seconds}         — objeto sumiu da cena por N segundos

Ações:
  banner_green / banner_red  {text, sound}  — banner na tela Ao Vivo + evento no log.
  Placeholders no texto: {nome} e {objeto}.

Disparo (trigger, por regra):
  {mode: "once"}                — 1x por aparição: dispara quando a condição passa a
                                  valer e re-arma quando ela deixa de valer por
                                  REARM_SECONDS (sujeito saiu da cena, boné voltou...)
  {mode: "interval", seconds}   — repete a cada N segundos enquanto a condição valer

Para evitar disparo por falha de um único frame, cada condição precisa se
manter verdadeira por um período de carência (grace) antes de disparar.
"""
import time
import uuid

REARM_SECONDS = 3.0

GRACE = {
    "person_recognized": 0.0,
    "unknown_person": 1.0,
    "object_detected": 0.0,
    "person_with_object": 1.0,
    "person_without_object": 2.5,
    "object_absent": None,  # usa condition.seconds (padrão 5)
}

CONDITION_LABELS = {
    "person_recognized": "Pessoa reconhecida",
    "unknown_person": "Pessoa desconhecida detectada",
    "object_detected": "Objeto detectado",
    "person_with_object": "Pessoa COM objeto",
    "person_without_object": "Pessoa SEM objeto",
    "object_absent": "Objeto ausente da cena",
}


def default_rules() -> list[dict]:
    def rule(name, condition, action, trigger):
        return {"id": uuid.uuid4().hex[:8], "name": name, "enabled": True,
                "condition": condition, "action": action, "trigger": trigger}

    return [
        rule(
            "Acesso liberado",
            {"type": "person_recognized", "person_id": None},
            {"type": "banner_green", "text": "ACESSO LIBERADO — {nome}", "sound": False},
            {"mode": "once"},
        ),
        rule(
            "Alerta de desconhecido",
            {"type": "unknown_person"},
            {"type": "banner_red", "text": "PESSOA NÃO RECONHECIDA", "sound": True},
            {"mode": "once"},
        ),
        rule(
            "Sem boné",
            {"type": "person_without_object", "person_id": None, "object": "baseball cap"},
            {"type": "banner_red", "text": "{nome} SEM BONÉ", "sound": True},
            {"mode": "interval", "seconds": 10},
        ),
        rule(
            "Buscar água",
            {"type": "object_absent", "object": "bottle", "seconds": 5},
            {"type": "banner_red", "text": "GARRAFA AUSENTE — BUSCAR ÁGUA", "sound": False},
            {"mode": "interval", "seconds": 15},
        ),
    ]


def _boxes_associated(face_bbox, obj_bbox) -> bool:
    """Associação geométrica rosto×objeto (ex.: capacete sobre a cabeça).

    Expande a caixa do rosto (mais para cima, onde fica capacete/óculos/máscara,
    e para baixo cobrindo o tronco, onde ficam crachá/colete) e testa interseção.
    """
    fx1, fy1, fx2, fy2 = face_bbox
    fw, fh = fx2 - fx1, fy2 - fy1
    zx1, zx2 = fx1 - fw * 1.5, fx2 + fw * 1.5
    zy1, zy2 = fy1 - fh * 1.5, fy2 + fh * 3.0
    ox1, oy1, ox2, oy2 = obj_bbox
    return not (ox2 < zx1 or ox1 > zx2 or oy2 < zy1 or oy1 > zy2)


class RuleEngine:
    def __init__(self, bus, object_engine):
        self._bus = bus
        self._objects = object_engine
        self._rules: list[dict] = []
        # estado por (regra, sujeito): quando a condição começou a valer, quando
        # foi vista verdadeira pela última vez e quando disparou
        self._state: dict[str, dict] = {}
        self._last_seen: dict[str, float] = {}  # classe de objeto -> último ts visto

    def load(self, rules: list[dict]) -> None:
        self._rules = rules

    def evaluate(self, faces: list[dict], objects: list[dict]) -> None:
        """Chamado a cada frame processado com o estado da cena."""
        now = time.time()
        for obj in objects:
            self._last_seen[obj["cls"]] = now

        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            grace = GRACE[rule["condition"]["type"]]
            if grace is None:
                grace = float(rule["condition"].get("seconds", 5))
            trigger = rule.get("trigger") or {}
            mode = trigger.get("mode", "interval")
            interval = float(trigger.get("seconds", 10))

            for subject_key, context in self._matches(rule["condition"], faces, objects, now):
                key = f"{rule['id']}:{subject_key}"
                st = self._state.setdefault(key, {"since": now, "fired_at": None})
                st["last"] = now
                if now - st["since"] < grace:
                    continue
                due = st["fired_at"] is None or (
                    mode == "interval" and now - st["fired_at"] >= interval
                )
                if due:
                    st["fired_at"] = now
                    self._fire(rule, context)

        # re-arma sujeitos cuja condição deixou de valer por REARM_SECONDS
        # (a tolerância evita re-disparo por falha de detecção de um frame)
        for key in [k for k, st in self._state.items() if now - st["last"] > REARM_SECONDS]:
            del self._state[key]

    def _matches(self, cond: dict, faces: list[dict], objects: list[dict], now: float):
        """Gera (chave_do_sujeito, contexto) para cada sujeito que satisfaz a condição."""
        ctype = cond["type"]
        recognized = [f for f in faces if f["name"]]
        if cond.get("person_id"):
            recognized = [f for f in recognized if f["person_id"] == cond["person_id"]]

        if ctype == "person_recognized":
            for f in recognized:
                yield f["person_id"], {"nome": f["name"]}

        elif ctype == "unknown_person":
            if any(f["name"] is None for f in faces):
                yield "unknown", {"nome": "Desconhecido"}

        elif ctype == "object_detected":
            hits = [o for o in objects if o["cls"] == cond["object"]]
            if hits:
                yield cond["object"], {"objeto": hits[0]["label"]}

        elif ctype in ("person_with_object", "person_without_object"):
            targets = [o for o in objects if o["cls"] == cond["object"]]
            label = self._objects.label(cond["object"]) if self._objects else cond["object"]
            for f in recognized:
                has = any(_boxes_associated(f["bbox"], o["bbox"]) for o in targets)
                if has == (ctype == "person_with_object"):
                    yield f["person_id"], {"nome": f["name"], "objeto": label}

        elif ctype == "object_absent":
            last = self._last_seen.get(cond["object"])
            absent_for = now - last if last else float("inf")
            window = max(
                float(cond.get("seconds", 5)),
                getattr(self._objects, "min_absence_window", 0.0),
            )
            if absent_for >= window:
                label = self._objects.label(cond["object"]) if self._objects else cond["object"]
                yield cond["object"], {"objeto": label}

    def _fire(self, rule: dict, context: dict) -> None:
        action = rule["action"]
        text = action.get("text", rule["name"])
        for placeholder, value in context.items():
            text = text.replace("{" + placeholder + "}", str(value))
        color = "green" if action["type"] == "banner_green" else "red"
        # o ritmo de disparo já é controlado pelo trigger da regra
        self._bus.emit("rule", text, cooldown=0, rule=rule["name"], color=color)
        self._bus.set_banner(color, text, duration=4.0, sound=action.get("sound", False))
