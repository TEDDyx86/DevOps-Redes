"""Motor do painel de ataques: fila com um ataque por vez, fases e eventos."""
import copy
import json
import queue
import threading
import time
import uuid
from datetime import datetime, timezone

from scripts.attack_panel import catalog

FINAL = ("concluido", "interrompido", "falhou")


class Cancelled(Exception):
    """Sinal interno de interrupção solicitada."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _format(event):
    return "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"


class AttackContext:
    def __init__(self, publish):
        self._publish = publish
        self._lock = threading.Lock()
        self.expected_alerts = []
        self.counters = {}
        self._cancel = threading.Event()

    def cancelled(self):
        return self._cancel.is_set()

    def check_cancelled(self):
        if self.cancelled():
            raise Cancelled()

    def request_cancel(self):
        self._cancel.set()

    def set_expected_alerts(self, alerts):
        with self._lock:
            self.expected_alerts = list(alerts)

    def log(self, message):
        self._publish("log", message=str(message))

    def progress(self, **counters):
        with self._lock:
            self.counters.update(counters)
            snapshot = dict(self.counters)
        self._publish("progress", counters=snapshot)

    def snapshot(self):
        with self._lock:
            return {"counters": dict(self.counters), "expected_alerts": list(self.expected_alerts)}


class Engine:
    def __init__(self, runners, verifier):
        self._runners = runners
        self._verifier = verifier
        self._lock = threading.Lock()
        self._wakeup = threading.Event()
        self._stopping = threading.Event()
        self._queue = []
        self._current = None
        self._contexts = {}
        self._history = []
        self._events = []
        self._seq = 0
        self._subscribers = []
        self._worker = threading.Thread(target=self._loop, name="attack-engine", daemon=True)
        self._worker.start()

    def enqueue(self, attack_id, params=None):
        cleaned = catalog.clean_params(attack_id, params)
        entry = {"entry_id": uuid.uuid4().hex, "attack": attack_id, "status": "agendado",
                 "params": cleaned, "expected_alerts": catalog.expected_alerts(attack_id),
                 "counters": {}, "verification": None, "error": None,
                 "started_at": None, "ended_at": None}
        with self._lock:
            self._queue.append(entry)
        self._publish("status", entry_id=entry["entry_id"], attack=attack_id, status="agendado", message="Ataque na fila")
        self._wakeup.set()
        return self._view(entry)

    def cancel(self, entry_id):
        with self._lock:
            current = self._current
            if current is not None and current["entry_id"] == entry_id:
                context = self._contexts.get(entry_id)
            else:
                context = None
                for index, entry in enumerate(self._queue):
                    if entry["entry_id"] == entry_id:
                        del self._queue[index]
                        break
                else:
                    return None
        if context is not None:
            context.request_cancel()
        self._publish("status", entry_id=entry_id, status="interrompendo", message="Interrupção solicitada")
        return {"entry_id": entry_id, "status": "interrompendo"}

    def snapshot(self):
        with self._lock:
            return {"current": self._view(self._current) if self._current else None,
                    "queue": [self._view(entry) for entry in self._queue],
                    "history": [dict(entry) for entry in self._history]}

    def recent_events(self, limit=200):
        with self._lock:
            return copy.deepcopy(self._events[-limit:])

    def subscribe(self):
        mailbox = queue.Queue()
        with self._lock:
            backlog = list(self._events)
            self._subscribers.append(mailbox)

        def stream():
            try:
                for event in backlog:
                    yield _format(event)
                while True:
                    try:
                        event = mailbox.get(timeout=15)
                    except queue.Empty:
                        yield ": ping\n\n"
                        continue
                    yield _format(event)
            finally:
                with self._lock:
                    if mailbox in self._subscribers:
                        self._subscribers.remove(mailbox)

        return stream()

    def stop(self):
        self._stopping.set()
        self._wakeup.set()
        self._worker.join(timeout=5)

    # ---- interno ------------------------------------------------------
    def _publish(self, event_type, **payload):
        with self._lock:
            self._seq += 1
            event = {"seq": self._seq, "type": event_type, **payload}
            self._events.append(event)
            if len(self._events) > 500:
                self._events.pop(0)
            for mailbox in self._subscribers:
                mailbox.put(event)

    def _view(self, entry):
        view = dict(entry)
        context = self._contexts.get(entry["entry_id"])
        if context is not None:
            state = context.snapshot()
            view["counters"] = state["counters"]
            view["expected_alerts"] = state["expected_alerts"]
        return view

    def _loop(self):
        while not self._stopping.is_set():
            self._wakeup.wait(0.2)
            self._wakeup.clear()
            with self._lock:
                if self._current is None and self._queue:
                    entry = self._queue.pop(0)
                    self._current = entry
                    entry["status"] = "preparando"
                    entry["started_at"] = _now()
                else:
                    entry = None
            if entry is not None:
                self._run(entry)

    def _run(self, entry):
        attack_id = entry["attack"]
        context = AttackContext(lambda event_type, **payload: self._publish(
            event_type, entry_id=entry["entry_id"], attack=attack_id, **payload))
        with self._lock:
            self._contexts[entry["entry_id"]] = context
            entry["status"] = "executando"
        self._publish("status", entry_id=entry["entry_id"], attack=attack_id, status="executando", message="Executando ataque")
        try:
            self._runners[attack_id](context, dict(entry["params"]))
            with self._lock:
                entry["status"] = "verificando"
            self._publish("status", entry_id=entry["entry_id"], status="verificando", message="Verificando alertas no Prometheus")
            result = self._verifier(context.snapshot()["expected_alerts"], context.cancelled)
            with self._lock:
                entry["verification"] = result
            self._publish("verification", entry_id=entry["entry_id"], data=result)
            entry["status"] = "concluido"
        except Cancelled:
            entry["status"] = "interrompido"
        except Exception as error:
            entry["status"] = "falhou"
            entry["error"] = type(error).__name__
        finally:
            state = context.snapshot()
            entry["counters"] = state["counters"]
            with self._lock:
                entry["ended_at"] = _now()
                self._history.append(entry)
                if len(self._history) > 10:
                    self._history.pop(0)
                self._current = None
                self._contexts.pop(entry["entry_id"], None)
            self._publish("status", entry_id=entry["entry_id"], attack=attack_id, status=entry["status"], message="Fim do ataque")
            self._wakeup.set()
