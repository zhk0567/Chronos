from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from context.align_engine import align_contexts, compute_completeness
from pipeline.cancel_registry import (
    AnalysisCancelledError,
    check_cancel,
    clear_run,
    register_run,
)
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
from pipeline.weather_insights import analyze_weather_insights
from llm.ollama_client import OllamaClient
from pipeline.artifacts import get_data_dir, save_run_artifact
from pipeline.checkpoint import (
    entry_fingerprint,
    load_anchors,
    load_chains,
    load_contexts,
    load_emotion,
    load_environment,
    load_factors,
    load_interactions,
    load_language,
    load_morphs,
    load_physio,
    load_reframe_candidates,
    load_relationships,
    load_selves,
    load_story,
    load_themes,
    load_units,
    load_warnings,
    resume_step_index,
    save_checkpoint,
)
from pipeline.steps import STEPS
from schemas.models import AnalysisProgress, DiaryEntry, InsightReport
from utils.baseline import save_emotion_baseline


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
        resume: bool = False,
    ) -> InsightReport:
        total = len(STEPS)
        ollama_ok = self.check_ollama()
        data_dir = get_data_dir()
        register_run(run_id)
        fingerprint = entry_fingerprint(entries)
        start_step = resume_step_index(run_id, entries, self.model) if resume else 0
        if resume and start_step >= total:
            raise ValueError("该分析已完成，无需续跑")

        ck = load_checkpoint(run_id) if resume else None
        started_at = datetime.now(timezone.utc).isoformat()
        if resume:
            meta_path = get_data_dir() / "analysis" / "runs" / run_id / "meta.json"
            if meta_path.exists():
                try:
                    started_at = json.loads(meta_path.read_text(encoding="utf-8")).get("startedAt", started_at)
                except Exception:
                    pass

        save_meta(
            run_id,
            {
                "runId": run_id,
                "startedAt": started_at,
                "status": "running",
                "entryCount": len(entries),
                "phase": 3,
                "resumedFromStep": STEPS[start_step - 1] if start_step > 0 else None,
            },
        )

        try:
            return self._run_steps(
                run_id,
                entries,
                on_progress,
                total,
                ollama_ok,
                data_dir,
                started_at,
                start_step,
                fingerprint,
            )
        except AnalysisCancelledError:
            ck_now = load_checkpoint(run_id)
            save_meta(
                run_id,
                {
                    "runId": run_id,
                    "startedAt": started_at,
                    "completedAt": datetime.now(timezone.utc).isoformat(),
                    "status": "paused",
                    "entryCount": len(entries),
                    "phase": 3,
                    "lastCompletedStep": ck_now.get("lastCompletedStep") if ck_now else None,
                },
            )
            raise
        finally:
            clear_run(run_id)

    def _run_steps(
        self,
        run_id: str,
        entries: list[DiaryEntry],
        on_progress: Optional[Callable[[AnalysisProgress], None]],
        total: int,
        ollama_ok: bool,
        data_dir: Path,
        started_at: str,
        start_step: int = 0,
        fingerprint: str = "",
    ) -> InsightReport:
        def progress(step_idx: int, message: str) -> None:
            check_cancel(run_id)
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

        def cp(step_idx: int) -> None:
            if fingerprint:
                save_checkpoint(run_id, step_idx, self.model, fingerprint)

        entries = sorted(entries, key=lambda e: e.date)
        dates = [e.date for e in entries]
        date_range = {"start": dates[0] if dates else "", "end": dates[-1] if dates else ""}

        bulk_llm = self._fast_llm() if len(entries) >= 15 and ollama_ok else self.llm
        close_bulk = bulk_llm is not self.llm

        # hydrate from checkpoint
        all_morphs = load_morphs(run_id) if start_step > 0 else []
        all_units = load_units(run_id) if start_step > 0 else []
        emotion_series = load_emotion(run_id) if start_step > 1 else []
        stability = analyze_stability(emotion_series, entries) if start_step > 1 else []
        daily_contexts = load_contexts(run_id) if start_step > 3 else []
        context_completeness = compute_completeness(daily_contexts) if start_step > 3 else {}
        anchors = load_anchors(run_id) if start_step > 4 else []
        promoting, damaging = load_factors(run_id) if start_step > 5 else ([], [])
        relationships = load_relationships(run_id) if start_step > 6 else []
        interactions = load_interactions(run_id) if start_step > 7 else []
        weather_insights: list = []
        env_sensitivity, space_emotions, weather_insights = (
            load_environment(run_id) if start_step > 8 else ([], [], [])
        )
        physio = load_physio(run_id) if start_step > 9 else []
        warnings = load_warnings(run_id) if start_step > 10 else []
        language_patterns = load_language(run_id) if start_step > 11 else []
        themes = load_themes(run_id) if start_step > 12 else []
        chain_links = load_chains(run_id) if start_step > 13 else []
        life_story = load_story(run_id) if start_step > 14 else None
        self_voice_map = load_selves(run_id) if start_step > 15 else None
        reframe_candidates = load_reframe_candidates(run_id) if start_step > 16 else []

        if start_step <= 0:
            progress(0, "Morph classification and unit extraction (batched)...")
            extract_llm = self._extract_llm(len(entries))

            def on_extract_batch(done: int, total_batches: int) -> None:
                check_cancel(run_id)
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
            cp(0)

        if start_step <= 1:
            progress(1, "Emotion scoring and stability...")
            emotion_series = score_emotions(entries, bulk_llm, self.use_llm and ollama_ok)
            stability = analyze_stability(emotion_series, entries)
            save_emotion_baseline(data_dir, emotion_series)
            save_run_artifact(run_id, "emotion.json", [p.model_dump(by_alias=True) for p in emotion_series])
            cp(1)

        if start_step <= 2:
            progress(2, "Loading context data sources...")
            ingest_context(data_dir, dates)
            cp(2)

        if start_step <= 3:
            progress(3, "Aligning multi-source context...")
            daily_contexts = align_contexts(data_dir, dates, all_units)
            context_completeness = compute_completeness(daily_contexts)
            save_run_artifact(
                run_id,
                "context.json",
                [c.model_dump(by_alias=True) for c in daily_contexts],
            )
            save_run_artifact(run_id, "units.json", [u.model_dump(by_alias=True) for u in all_units])
            cp(3)

        if start_step <= 4:
            progress(4, "Anchor detection...")
            anchors = detect_anchors(entries, all_morphs, all_units, emotion_series)
            save_run_artifact(run_id, "anchors.json", [a.model_dump(by_alias=True) for a in anchors])
            cp(4)

        if start_step <= 5:
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
            cp(5)

        if start_step <= 6:
            progress(6, "Relationship network...")
            relationships = analyze_network(all_units, emotion_series)
            save_run_artifact(run_id, "network.json", [r.model_dump(by_alias=True) for r in relationships])
            cp(6)

        if start_step <= 7:
            progress(7, "Interaction effects...")
            interactions = analyze_interactions(daily_contexts, emotion_series)
            save_run_artifact(run_id, "interactions.json", [i.model_dump(by_alias=True) for i in interactions])
            cp(7)

        if start_step <= 8:
            progress(8, "Environment sensitivity...")
            env_sensitivity = analyze_weather_sensitivity(daily_contexts, emotion_series)
            weather_insights = analyze_weather_insights(daily_contexts, emotion_series, env_sensitivity)
            space_emotions = analyze_space_emotion(daily_contexts, emotion_series, all_units)
            save_run_artifact(run_id, "environment.json", {
                "sensitivity": [s.model_dump(by_alias=True) for s in env_sensitivity],
                "space": [s.model_dump(by_alias=True) for s in space_emotions],
                "insights": [w.model_dump(by_alias=True) for w in weather_insights],
            })
            cp(8)

        if start_step <= 9:
            progress(9, "Physio-psychological coupling...")
            physio = analyze_physio_coupling(daily_contexts, emotion_series)
            save_run_artifact(run_id, "physio.json", [p.model_dump(by_alias=True) for p in physio])
            cp(9)

        if start_step <= 10:
            progress(10, "Warning pattern detection...")
            warnings = detect_warning_patterns(daily_contexts, emotion_series)
            save_run_artifact(run_id, "warnings.json", [w.model_dump(by_alias=True) for w in warnings])
            cp(10)

        if start_step <= 11:
            progress(11, "Language patterns...")
            language_patterns = analyze_language(entries, bulk_llm, self.use_llm and ollama_ok)
            save_run_artifact(run_id, "language.json", [l.model_dump(by_alias=True) for l in language_patterns])
            cp(11)

        if start_step <= 12:
            progress(12, "Theme lifecycle...")
            themes = analyze_themes(entries, emotion_series, bulk_llm, self.use_llm and ollama_ok)
            save_run_artifact(run_id, "themes.json", [t.model_dump(by_alias=True) for t in themes])
            cp(12)

        if start_step <= 13:
            progress(13, "Building anchor chain links...")
            anchors, chain_links = build_chain_links(
                anchors, all_units, themes, relationships, entries, emotion_series
            )
            save_run_artifact(run_id, "anchors.json", [a.model_dump(by_alias=True) for a in anchors])
            save_run_artifact(run_id, "chains.json", [c.model_dump(by_alias=True) for c in chain_links])
            cp(13)

        if start_step <= 14:
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
            cp(14)

        if start_step <= 15:
            progress(15, "Analyzing self voices...")
            self_voice_map = analyze_selves(all_units, emotion_series)
            save_run_artifact(run_id, "selves.json", self_voice_map.model_dump(by_alias=True))
            cp(15)

        if start_step <= 16:
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
            cp(16)

        if start_step <= 17:
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
                weather_insights=weather_insights or analyze_weather_insights(
                    daily_contexts, emotion_series, env_sensitivity
                ),
            )

            run_dir = data_dir / "analysis" / "runs" / run_id
            report_json = report.model_dump(by_alias=True)
            (run_dir / "report.json").write_text(
                json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (run_dir / "report.html").write_text(render_html(report), encoding="utf-8")
            cp(17)

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

        raise ValueError("无可执行的续跑步骤")
