from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from context.align_engine import align_contexts, compute_completeness
from pipeline.chain_link_builder import build_chain_links
from pipeline.context_ingest import ingest_context
from pipeline.problem_narrative_detector import detect_problem_narratives
from pipeline.selves_analyzer import analyze_selves
from pipeline.story_builder import build_life_story
from pipeline.anchor_detector import detect_anchors
from pipeline.controlled_factors import analyze_controlled_factors
from pipeline.emotion_analyzer import analyze_stability, score_emotions
from pipeline.interaction_analyzer import analyze_interactions
from pipeline.language_analyzer import analyze_language
from pipeline.morph_classifier import extract_all_morph_and_units
from pipeline.network_analyzer import analyze_network
from pipeline.physio_coupling import analyze_physio_coupling
from pipeline.report_builder import build_report, render_html
from pipeline.space_emotion import analyze_space_emotion
from pipeline.theme_analyzer import analyze_themes
from pipeline.warning_detector import detect_warning_patterns
from pipeline.weather_sensitivity import analyze_weather_sensitivity
from llm.ollama_client import OllamaClient
from schemas.models import AnalysisProgress, DiaryEntry, InsightReport


STEPS = [
    "extract",
    "emotion",
    "context",
    "align",
    "anchors",
    "factors",
    "network",
    "interaction",
    "environment",
    "physio",
    "warning",
    "language",
    "themes",
    "chains",
    "story",
    "selves",
    "reframe",
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
    EXTRACT_BATCH_SIZE = 20

    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
        self.llm = OllamaClient(model=model)
        self.use_llm = True

    def _fast_llm(self) -> OllamaClient:
        fast = os.environ.get("CHRONOS_FAST_MODEL", os.environ.get("CHRONOS_EXTRACT_MODEL", "gemma3:4b"))
        if self.llm.model == fast:
            return self.llm
        return OllamaClient(model=fast)

    def _extract_llm(self, entry_count: int) -> OllamaClient:
        """Use local fast model for bulk extract when many entries."""
        if entry_count >= 15 and self.use_llm:
            return self._fast_llm()
        return self.llm

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
        data_dir = get_data_dir()

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
                "phase": 3,
            },
        )

        entries = sorted(entries, key=lambda e: e.date)
        dates = [e.date for e in entries]
        date_range = {"start": dates[0] if dates else "", "end": dates[-1] if dates else ""}

        # Step 1: Extract (batched)
        progress(0, "Morph classification and unit extraction (batched)...")
        extract_llm = self._extract_llm(len(entries))

        def on_extract_batch(done: int, total_batches: int) -> None:
            if on_progress:
                on_progress(
                    AnalysisProgress(
                        runId=run_id,
                        step="extract",
                        stepIndex=1,
                        totalSteps=total,
                        message=f"Extract batch {done}/{total_batches}...",
                        percent=round(done / max(total_batches, 1) * (100 / total), 1),
                    )
                )

        all_morphs, all_units = extract_all_morph_and_units(
            entries,
            extract_llm,
            self.use_llm and ollama_ok,
            batch_size=self.EXTRACT_BATCH_SIZE,
            on_batch=on_extract_batch,
        )
        if extract_llm is not self.llm:
            extract_llm.close()
        save_run_artifact(run_id, "morphs.json", [m.model_dump(by_alias=True) for m in all_morphs])
        save_run_artifact(run_id, "units.json", [u.model_dump(by_alias=True) for u in all_units])

        bulk_llm = self._fast_llm() if len(entries) >= 15 and ollama_ok else self.llm
        close_bulk = bulk_llm is not self.llm

        # Step 2: Emotion
        progress(1, "Emotion scoring and stability...")
        emotion_series = score_emotions(entries, bulk_llm, self.use_llm and ollama_ok)
        stability = analyze_stability(emotion_series, entries)
        save_run_artifact(run_id, "emotion.json", [p.model_dump(by_alias=True) for p in emotion_series])

        # Step 3: Context ingest (weather prefetch)
        progress(2, "Loading context data sources...")
        ingest_context(data_dir, dates)

        # Step 4: Align
        progress(3, "Aligning multi-source context...")
        daily_contexts = align_contexts(data_dir, dates, all_units)
        context_completeness = compute_completeness(daily_contexts)
        save_run_artifact(
            run_id,
            "context.json",
            [c.model_dump(by_alias=True) for c in daily_contexts],
        )
        save_run_artifact(run_id, "units.json", [u.model_dump(by_alias=True) for u in all_units])

        # Step 5: Anchors
        progress(4, "Anchor detection...")
        anchors = detect_anchors(entries, all_morphs, all_units, emotion_series)
        save_run_artifact(run_id, "anchors.json", [a.model_dump(by_alias=True) for a in anchors])

        # Step 6: Controlled factors
        progress(5, "Controlled factor analysis...")
        promoting, damaging = analyze_controlled_factors(all_units, emotion_series, daily_contexts)
        save_run_artifact(
            run_id,
            "factors.json",
            {
                "promoting": [f.model_dump(by_alias=True) for f in promoting],
                "damaging": [f.model_dump(by_alias=True) for f in damaging],
            },
        )

        # Step 7: Network
        progress(6, "Relationship network...")
        relationships = analyze_network(all_units, emotion_series)
        save_run_artifact(run_id, "network.json", [r.model_dump(by_alias=True) for r in relationships])

        # Step 8: Interaction
        progress(7, "Interaction effects...")
        interactions = analyze_interactions(daily_contexts, emotion_series)
        save_run_artifact(run_id, "interactions.json", [i.model_dump(by_alias=True) for i in interactions])

        # Step 9: Environment sensitivity
        progress(8, "Environment sensitivity...")
        env_sensitivity = analyze_weather_sensitivity(daily_contexts, emotion_series)
        space_emotions = analyze_space_emotion(daily_contexts, emotion_series, all_units)
        save_run_artifact(run_id, "environment.json", {
            "sensitivity": [s.model_dump(by_alias=True) for s in env_sensitivity],
            "space": [s.model_dump(by_alias=True) for s in space_emotions],
        })

        # Step 10: Physio coupling
        progress(9, "Physio-psychological coupling...")
        physio = analyze_physio_coupling(daily_contexts, emotion_series)
        save_run_artifact(run_id, "physio.json", [p.model_dump(by_alias=True) for p in physio])

        # Step 11: Warning patterns
        progress(10, "Warning pattern detection...")
        warnings = detect_warning_patterns(daily_contexts, emotion_series)
        save_run_artifact(run_id, "warnings.json", [w.model_dump(by_alias=True) for w in warnings])

        # Step 12: Language
        progress(11, "Language patterns...")
        language_patterns = analyze_language(entries, bulk_llm, self.use_llm and ollama_ok)
        save_run_artifact(run_id, "language.json", [l.model_dump(by_alias=True) for l in language_patterns])

        # Step 13: Themes
        progress(12, "Theme lifecycle...")
        themes = analyze_themes(entries, emotion_series, bulk_llm, self.use_llm and ollama_ok)
        save_run_artifact(run_id, "themes.json", [t.model_dump(by_alias=True) for t in themes])

        # Step 15: Chain links
        progress(13, "Building anchor chain links...")
        anchors, chain_links = build_chain_links(
            anchors, all_units, themes, relationships, entries, emotion_series
        )
        save_run_artifact(run_id, "anchors.json", [a.model_dump(by_alias=True) for a in anchors])
        save_run_artifact(run_id, "chains.json", [c.model_dump(by_alias=True) for c in chain_links])

        # Step 16: Life story
        progress(14, "Building life story...")
        life_story = build_life_story(
            run_id,
            anchors,
            chain_links,
            themes,
            relationships,
            emotion_series,
            data_dir,
            self.llm,
            self.use_llm and ollama_ok,
        )
        save_run_artifact(run_id, "story.json", life_story.model_dump(by_alias=True))

        # Step 17: Selves
        progress(15, "Analyzing self voices...")
        self_voice_map = analyze_selves(all_units, emotion_series)
        save_run_artifact(run_id, "selves.json", self_voice_map.model_dump(by_alias=True))

        # Step 18: Reframe candidates
        progress(16, "Detecting problem narratives...")
        reframe_candidates = detect_problem_narratives(
            entries,
            emotion_series,
            damaging,
            bulk_llm,
            self.use_llm and ollama_ok,
        )
        save_run_artifact(
            run_id,
            "reframe_candidates.json",
            [c.model_dump(by_alias=True) for c in reframe_candidates],
        )

        # Step 19: Report
        progress(17, "Generating insight report...")
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
            daily_contexts=daily_contexts,
            environment_sensitivity=env_sensitivity,
            space_emotions=space_emotions,
            physio_couplings=physio,
            interaction_effects=interactions,
            warning_patterns=warnings,
            context_completeness=context_completeness,
            chain_links=chain_links,
            life_story=life_story,
            self_voice_map=self_voice_map,
            reframe_candidates=reframe_candidates,
        )

        run_dir = data_dir / "analysis" / "runs" / run_id
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
                "phase": 3,
            },
        )

        self.llm.close()
        if close_bulk:
            bulk_llm.close()
        return report
