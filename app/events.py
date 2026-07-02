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
            return True

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
