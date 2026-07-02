"""Log de eventos em memória com cooldown/dedup, consumido via SSE."""
import threading
import time
from collections import deque
from datetime import datetime


class EventBus:
    def __init__(self, maxlen: int = 500):
        self._lock = threading.Lock()
        self._events: deque[dict] = deque(maxlen=maxlen)
        self._seq = 0
        self._cooldowns: dict[str, float] = {}
        # banner ativo na tela Ao Vivo (setado pelas regras)
        self._banner: dict | None = None
        # contadores de sessão (alimentam o dashboard)
        self._started = time.time()
        self._counters = {"identificacoes": 0, "desconhecidos": 0,
                          "objetos": 0, "regras": 0, "eventos": 0}
        self._conf_sum = 0.0
        self._conf_count = 0

    def emit(
        self,
        kind: str,
        message: str,
        *,
        dedupe_key: str | None = None,
        cooldown: float = 10.0,
        **meta,
    ) -> bool:
        now = time.time()
        with self._lock:
            key = dedupe_key or f"{kind}:{message}"
            if now - self._cooldowns.get(key, 0.0) < cooldown:
                return False
            self._cooldowns[key] = now
            self._seq += 1
            self._events.append(
                {
                    "id": self._seq,
                    "kind": kind,
                    "message": message,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    **meta,
                }
            )
            self._count(kind, dedupe_key, meta)
            return True

    def _count(self, kind: str, dedupe_key: str | None, meta: dict) -> None:
        if kind != "system":
            self._counters["eventos"] += 1
        if kind == "face":
            if dedupe_key == "face:unknown":
                self._counters["desconhecidos"] += 1
            else:
                self._counters["identificacoes"] += 1
                if meta.get("confidence"):
                    self._conf_sum += float(meta["confidence"])
                    self._conf_count += 1
        elif kind == "object":
            self._counters["objetos"] += 1
        elif kind == "rule":
            self._counters["regras"] += 1

    def stats(self) -> dict:
        with self._lock:
            precisao = (
                round(self._conf_sum / self._conf_count * 100, 1)
                if self._conf_count else None
            )
            return {
                **self._counters,
                "precisao": precisao,
                "uptime_s": int(time.time() - self._started),
            }

    def set_banner(self, color: str, text: str, duration: float = 4.0, sound: bool = False):
        with self._lock:
            self._banner = {
                "color": color,
                "text": text,
                "sound": sound,
                "until": time.time() + duration,
            }

    def snapshot(self, after_id: int = 0) -> dict:
        """Eventos novos + estado atual do banner (para o SSE)."""
        with self._lock:
            events = [e for e in self._events if e["id"] > after_id]
            banner = None
            if self._banner and self._banner["until"] > time.time():
                banner = {k: self._banner[k] for k in ("color", "text", "sound")}
            return {"events": events, "banner": banner}
