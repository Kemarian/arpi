"""Thread-safe application state — the single source of truth for status + results."""

from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field


class PipelineStatus(str, enum.Enum):
    """What the vision pipeline is currently doing."""

    IDLE = "idle"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


@dataclass
class VisionResult:
    """Last analysis result."""

    text: str = ""
    timestamp: str = ""
    error: str = ""


@dataclass
class HealthSnapshot:
    """Reported to Unity via /health."""

    status: str = "ok"
    camera: bool = False
    button: bool = False
    uptime_s: int = 0


class AppState:
    """Thread-safe mutable state shared between button listener and HTTP server.

    Only this class is allowed to mutate state.
    Readers (Flask routes) call snapshot methods which return immutable copies.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.monotonic()
        self._pipeline: PipelineStatus = PipelineStatus.IDLE
        self._result = VisionResult()
        self._camera_ok: bool = False
        self._button_ok: bool = False

    # ── Writers (called from pipeline / button thread) ───────────────────

    def set_camera_ok(self, ok: bool) -> None:
        with self._lock:
            self._camera_ok = ok

    def set_button_ok(self, ok: bool) -> None:
        with self._lock:
            self._button_ok = ok

    def mark_processing(self) -> None:
        with self._lock:
            self._pipeline = PipelineStatus.PROCESSING
            self._result = VisionResult()  # clear previous

    def mark_ready(self, text: str, timestamp: str) -> None:
        with self._lock:
            self._pipeline = PipelineStatus.READY
            self._result = VisionResult(text=text, timestamp=timestamp)

    def mark_error(self, error: str) -> None:
        with self._lock:
            self._pipeline = PipelineStatus.ERROR
            self._result = VisionResult(error=error)

    def mark_idle(self) -> None:
        with self._lock:
            self._pipeline = PipelineStatus.IDLE

    # ── Readers (called from Flask routes) ───────────────────────────────

    @property
    def pipeline_status(self) -> PipelineStatus:
        with self._lock:
            return self._pipeline

    def get_health(self) -> HealthSnapshot:
        with self._lock:
            return HealthSnapshot(
                status="ok",
                camera=self._camera_ok,
                button=self._button_ok,
                uptime_s=int(time.monotonic() - self._start_time),
            )

    def get_result(self) -> dict:
        with self._lock:
            return {
                "status": self._pipeline.value,
                "text": self._result.text,
                "timestamp": self._result.timestamp,
                "error": self._result.error,
            }
