from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

from pipeline.anchor_detector import detect_anchors
from pipeline.emotion_analyzer import analyze_stability, score_emotions
from pipeline.factor_analyzer import analyze_factors
from pipeline.language_analyzer import analyze_language
from pipeline.morph_classifier import extract_morph_and_units
from pipeline.network_analyzer import analyze_network
from pipeline.report_builder import build_report, render_html
from pipeline.theme_analyzer import analyze_themes
from llm.ollama_client import OllamaClient
from schemas.models import AnalysisProgress, DiaryEntry, InsightReport


STEPS = [
    "extract",
    "emotion",
    "anchors",
    "factors",
    "network",
    "language",
    "themes",
    "report",
]


def get_data_dir() -> Path:
    return Path(os.environ.get("CHRONOS_DATA_DIR", "data"))


def save_run_artifact(run_id: str, name: str, data: dict | list) -> None:
    run_dir = get_data_dir() / "analysis" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_meta(run_id: str, meta: dict) -> None:
    save_run_artifact(run_id, "meta.json", meta)


class AnalysisPipeline:
    def __init__(self, model: str = "minimax-m3:cloud"):
        self.llm = OllamaClient(model=model)
        self.use_llm = True

    def check_ollama(self) -> bool:
        ok, _ = self.llm.check_health()
        if not ok:
            self.use_llm = False
        return ok

    def run(
        self,
        run_id: str,
        entries: list[DiaryEntry],
        on_progress: Optional[Callable[[AnalysisProgress], None]] = None,
    ) -> InsightReport:
        total = len(STEPS)
        ollama_ok = self.check_ollama()

        def progress(step_idx: int, message: str) -> None:
            if on_progress:
                on_progress(
                    AnalysisProgress(
                        runId=run_id,
                        step=STEPS[step_idx],
                        stepIndex=step_idx + 1,
                        totalSteps=total,
                        message=message,
                        percent=round((step_idx + 1) / total * 100, 1),
                    )
                )

        started_at = datetime.now(timezone.utc).isoformat()
        save_meta(
            run_id,
            {
                "runId": run_id,
                "startedAt": started_at,
                "status": "running",
                "entryCount": len(entries),
            },
        )

        entries = sorted(entries, key=lambda e: e.date)
        date_range = {
            "start": entries[0].date if entries else "",
            "end": entries[-1].date if entries else "",
        }

        # Step 1: Extract
        progress(0, "形态分类与信息单元抽取...")
        all_morphs = []
        all_units = []
        for entry in entries:
            morphs, units = extract_morph_and_units(entry, self.llm, self.use_llm and ollama_ok)
            all_morphs.extend(morphs)
            all_units.extend(units)
        save_run_artifact(run_id, "morphs.json", [m.model_dump(by_alias=True) for m in all_morphs])
        save_run_artifact(run_id, "units.json", [u.model_dump(by_alias=True) for u in all_units])

        # Step 2: Emotion
        progress(1, "情绪评分与稳定性分析...")
        emotion_series = score_emotions(entries, self.llm, self.use_llm and ollama_ok)
        stability = analyze_stability(emotion_series, entries)
        save_run_artifact(
            run_id,
            "emotion.json",
            [p.model_dump(by_alias=True) for p in emotion_series],
        )

        # Step 3: Anchors
        progress(2, "锚点涌现检测...")
        anchors = detect_anchors(entries, all_morphs, all_units, emotion_series)
        save_run_artifact(run_id, "anchors.json", [a.model_dump(by_alias=True) for a in anchors])

        # Step 4: Factors
        progress(3, "促进与损害因素识别...")
        promoting, damaging = analyze_factors(all_units, emotion_series)
        save_run_artifact(
            run_id,
            "factors.json",
            {
                "promoting": [f.model_dump(by_alias=True) for f in promoting],
                "damaging": [f.model_dump(by_alias=True) for f in damaging],
            },
        )

        # Step 5: Network
        progress(4, "关系网络分析...")
        relationships = analyze_network(all_units, emotion_series)
        save_run_artifact(
            run_id,
            "network.json",
            [r.model_dump(by_alias=True) for r in relationships],
        )

        # Step 6: Language
        progress(5, "语言与思维模式分析...")
        language_patterns = analyze_language(entries, self.llm, self.use_llm and ollama_ok)
        save_run_artifact(
            run_id,
            "language.json",
            [l.model_dump(by_alias=True) for l in language_patterns],
        )

        # Step 7: Themes
        progress(6, "主题生命周期分析...")
        themes = analyze_themes(entries, emotion_series, self.llm, self.use_llm and ollama_ok)
        save_run_artifact(run_id, "themes.json", [t.model_dump(by_alias=True) for t in themes])

        # Step 8: Report
        progress(7, "生成洞察报告...")
        report = build_report(
            run_id=run_id,
            entry_count=len(entries),
            date_range=date_range,
            anchors=anchors,
            emotion_series=emotion_series,
            stability=stability,
            promoting=promoting,
            damaging=damaging,
            relationships=relationships,
            language_patterns=language_patterns,
            themes=themes,
        )

        run_dir = get_data_dir() / "analysis" / "runs" / run_id
        report_json = report.model_dump(by_alias=True)
        (run_dir / "report.json").write_text(
            json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (run_dir / "report.html").write_text(render_html(report), encoding="utf-8")

        save_meta(
            run_id,
            {
                "runId": run_id,
                "startedAt": started_at,
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "entryCount": len(entries),
            },
        )

        self.llm.close()
        return report
