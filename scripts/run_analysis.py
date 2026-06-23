"""Run full Chronos analysis pipeline from CLI."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure engine package root is on path
ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(ENGINE_DIR))
os.chdir(ENGINE_DIR)

from pipeline.runner import AnalysisPipeline  # noqa: E402
from schemas.models import DiaryEntry  # noqa: E402


def main() -> int:
    data_dir = Path(os.environ.get("CHRONOS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
    entries_dir = data_dir / "entries"
    files = sorted(entries_dir.glob("2026-*.json"))
    if not files:
        print("ERROR: no 2026 entries found", file=sys.stderr)
        return 1

    entries = [DiaryEntry(**json.loads(f.read_text(encoding="utf-8"))) for f in files]
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"[chronos] 开始分析: {len(entries)} 篇日记, runId={run_id}", flush=True)

    def on_progress(p):
        print(f"  [{p.step_index}/{p.total_steps}] {p.step}: {p.message}", flush=True)

    report = AnalysisPipeline().run(run_id, entries, on_progress=on_progress)

    story_lines = len(report.life_story.lines) if report.life_story else 0
    profiles = len(report.self_voice_map.profiles) if report.self_voice_map else 0
    print(f"[chronos] 完成 runId={report.run_id}", flush=True)
    print(f"  锚点: {len(report.anchors)}", flush=True)
    print(f"  关联链: {len(report.chain_links)}", flush=True)
    print(f"  叙事线: {story_lines}", flush=True)
    print(f"  自我声音: {profiles}", flush=True)
    print(f"  重构候选: {len(report.reframe_candidates)}", flush=True)
    print(f"  报告板块: {len(report.sections)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
