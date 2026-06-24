from __future__ import annotations

import json
import os
from pathlib import Path


def get_data_dir() -> Path:
    return Path(os.environ.get("CHRONOS_DATA_DIR", "data"))


def save_run_artifact(run_id: str, name: str, data: dict | list) -> None:
    run_dir = get_data_dir() / "analysis" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
