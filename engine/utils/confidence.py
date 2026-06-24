"""Map numeric confidence to user-facing tier."""

from __future__ import annotations


def confidence_label(confidence: float) -> str:
    if confidence >= 0.7:
        return "高"
    if confidence >= 0.45:
        return "中"
    return "低"
