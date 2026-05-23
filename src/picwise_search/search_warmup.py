from __future__ import annotations

import logging
import threading
from typing import Callable, Literal

from picwise_search_memory.canonical_registry import get_cached_canonical_vocabulary_registry

from .index_resolver_adapter import get_cached_offline_search_index

logger = logging.getLogger(__name__)

SEARCH_WARMUP_DELAY_SECONDS = 0.75

WarmupState = Literal["not_started", "scheduled", "warming", "ready", "failed"]

_lock = threading.Lock()
_state: WarmupState = "not_started"
_timer: threading.Timer | None = None
_timer_factory: Callable[[float, Callable[[], None]], threading.Timer] = threading.Timer


def get_search_warmup_state() -> WarmupState:
    with _lock:
        return _state


def _run_warmup_task() -> None:
    global _state
    with _lock:
        if _state in ("ready", "warming"):
            return
        _state = "warming"

    try:
        get_cached_canonical_vocabulary_registry()
        get_cached_offline_search_index()
    except Exception:
        logger.exception("search warm-up failed")
        with _lock:
            _state = "failed"
        return

    with _lock:
        _state = "ready"


def _on_timer_fire() -> None:
    _run_warmup_task()


def schedule_search_warmup_if_needed(*, delay_seconds: float | None = None) -> None:
    global _timer, _state
    effective_delay = SEARCH_WARMUP_DELAY_SECONDS if delay_seconds is None else delay_seconds

    with _lock:
        if _state in ("scheduled", "warming", "ready"):
            return
        _state = "scheduled"
        _timer = _timer_factory(effective_delay, _on_timer_fire)
        _timer.daemon = True
        _timer.start()


def _reset_search_warmup_for_tests() -> None:
    global _timer, _state
    with _lock:
        if _timer is not None:
            _timer.cancel()
            _timer = None
        _state = "not_started"
