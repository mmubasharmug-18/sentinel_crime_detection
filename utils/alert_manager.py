"""
Alert Manager
-------------
Stores, retrieves, and serialises detection alerts.
Thread-safe; can be written by the detector thread and read by Dash callbacks.
"""

import threading
from datetime import datetime
from collections import deque

MAX_ALERTS = 200   # keep last N alerts in memory


class AlertManager:

    def __init__(self):
        self._alerts: deque = deque(maxlen=MAX_ALERTS)
        self._lock           = threading.Lock()
        self._total_count    = 0

    # ── write ─────────────────────────────────────────────────────────────

    def add(self, result: dict, source: str = "webcam"):
        with self._lock:
            self._total_count += 1
            self._alerts.appendleft({
                "id":         self._total_count,
                "time":       result.get("timestamp", datetime.now().strftime("%H:%M:%S")),
                "date":       result.get("date",      datetime.now().strftime("%Y-%m-%d")),
                "confidence": result.get("confidence", 0.0),
                "motion":     result.get("motion",     0.0),
                "source":     source,
                "severity":   _severity(result.get("confidence", 0.0)),
            })

    def clear(self):
        with self._lock:
            self._alerts.clear()
            self._total_count = 0

    # ── read ──────────────────────────────────────────────────────────────

    def get_all(self) -> list:
        with self._lock:
            return list(self._alerts)

    def get_recent(self, n: int = 10) -> list:
        with self._lock:
            return list(self._alerts)[:n]

    @property
    def total(self) -> int:
        with self._lock:
            return self._total_count

    def stats(self) -> dict:
        with self._lock:
            alerts = list(self._alerts)
        if not alerts:
            return {"total": 0, "high": 0, "medium": 0, "low": 0}
        return {
            "total":  len(alerts),
            "high":   sum(1 for a in alerts if a["severity"] == "HIGH"),
            "medium": sum(1 for a in alerts if a["severity"] == "MEDIUM"),
            "low":    sum(1 for a in alerts if a["severity"] == "LOW"),
        }


# ── helpers ───────────────────────────────────────────────────────────────

def _severity(confidence: float) -> str:
    if confidence >= 0.8:
        return "HIGH"
    if confidence >= 0.5:
        return "MEDIUM"
    return "LOW"


# ── singleton ─────────────────────────────────────────────────────────────
alert_manager = AlertManager()
