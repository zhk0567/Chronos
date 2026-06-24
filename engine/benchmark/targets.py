"""Benchmark quality targets (v0.2)."""

WARNING_RECALL_TARGET = 0.6
WARNING_PRECISION_TARGET = 0.3


def warning_targets_met(precision: float, recall: float) -> bool:
    return recall >= WARNING_RECALL_TARGET and precision >= WARNING_PRECISION_TARGET
