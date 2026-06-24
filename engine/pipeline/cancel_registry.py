from __future__ import annotations

import threading

_registry: dict[str, threading.Event] = {}


class AnalysisCancelledError(Exception):
    """Raised when user cancels a running analysis."""


def register_run(run_id: str) -> None:
    _registry[run_id] = threading.Event()


def cancel_run(run_id: str) -> bool:
    ev = _registry.get(run_id)
    if ev is None:
        return False
    ev.set()
    return True


def is_cancelled(run_id: str) -> bool:
    ev = _registry.get(run_id)
    return ev is not None and ev.is_set()


def check_cancel(run_id: str) -> None:
    if is_cancelled(run_id):
        raise AnalysisCancelledError(f"分析已取消 ({run_id})")


def clear_run(run_id: str) -> None:
    _registry.pop(run_id, None)
