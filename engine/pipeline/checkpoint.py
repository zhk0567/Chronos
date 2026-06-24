from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from schemas.models import (
    AnchorCard,
    ChainLink,
    DailyContext,
    EmotionPoint,
    FactorConclusion,
    InfoUnit,
    InteractionEffect,
    LanguageMetric,
    LifeStoryBook,
    MorphResult,
    PersonNode,
    PhysioCoupling,
    ReframeCandidate,
    SelfVoiceMap,
    ThemeTrack,
    WarningPattern,
    WeatherInsight,
    WeatherSensitivity,
    SpaceEmotionLink,
)
from pipeline.artifacts import get_data_dir, save_run_artifact
from pipeline.steps import STEPS


def entry_fingerprint(entries: list) -> str:
    key = "|".join(f"{e.date}:{len(e.content)}" for e in sorted(entries, key=lambda x: x.date))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _run_dir(run_id: str) -> Path:
    return get_data_dir() / "analysis" / "runs" / run_id


def save_checkpoint(run_id: str, step_idx: int, model: str, fingerprint: str) -> None:
    payload = {
        "lastCompletedStep": STEPS[step_idx],
        "lastCompletedStepIndex": step_idx,
        "model": model,
        "entryFingerprint": fingerprint,
    }
    save_run_artifact(run_id, "checkpoint.json", payload)


def load_checkpoint(run_id: str) -> dict[str, Any] | None:
    path = _run_dir(run_id) / "checkpoint.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resume_step_index(run_id: str, entries: list, model: str) -> int:
    ck = load_checkpoint(run_id)
    if not ck:
        return 0
    if ck.get("entryFingerprint") != entry_fingerprint(entries):
        raise ValueError("日记内容与上次分析不一致，无法续跑")
    if ck.get("model") and ck["model"] != model:
        pass  # allow model change on resume
    return int(ck.get("lastCompletedStepIndex", -1)) + 1


def _load_json(name: str, run_id: str) -> Any:
    path = _run_dir(run_id) / name
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact {name} for resume")
    return json.loads(path.read_text(encoding="utf-8"))


def load_morphs(run_id: str) -> list[MorphResult]:
    return [MorphResult(**m) for m in _load_json("morphs.json", run_id)]


def load_units(run_id: str) -> list[InfoUnit]:
    return [InfoUnit(**u) for u in _load_json("units.json", run_id)]


def load_emotion(run_id: str) -> list[EmotionPoint]:
    return [EmotionPoint(**p) for p in _load_json("emotion.json", run_id)]


def load_contexts(run_id: str) -> list[DailyContext]:
    return [DailyContext(**c) for c in _load_json("context.json", run_id)]


def load_anchors(run_id: str) -> list[AnchorCard]:
    return [AnchorCard(**a) for a in _load_json("anchors.json", run_id)]


def load_factors(run_id: str) -> tuple[list[FactorConclusion], list[FactorConclusion]]:
    data = _load_json("factors.json", run_id)
    promoting = [FactorConclusion(**f) for f in data.get("promoting", [])]
    damaging = [FactorConclusion(**f) for f in data.get("damaging", [])]
    return promoting, damaging


def load_relationships(run_id: str) -> list[PersonNode]:
    return [PersonNode(**r) for r in _load_json("network.json", run_id)]


def load_interactions(run_id: str) -> list[InteractionEffect]:
    return [InteractionEffect(**i) for i in _load_json("interactions.json", run_id)]


def load_environment(
    run_id: str,
) -> tuple[list[WeatherSensitivity], list[SpaceEmotionLink], list[WeatherInsight]]:
    data = _load_json("environment.json", run_id)
    sensitivity = [WeatherSensitivity(**s) for s in data.get("sensitivity", [])]
    space = [SpaceEmotionLink(**s) for s in data.get("space", [])]
    insights = [WeatherInsight(**w) for w in data.get("insights", [])]
    return sensitivity, space, insights


def load_physio(run_id: str) -> list[PhysioCoupling]:
    return [PhysioCoupling(**p) for p in _load_json("physio.json", run_id)]


def load_warnings(run_id: str) -> list[WarningPattern]:
    return [WarningPattern(**w) for w in _load_json("warnings.json", run_id)]


def load_language(run_id: str) -> list[LanguageMetric]:
    return [LanguageMetric(**l) for l in _load_json("language.json", run_id)]


def load_themes(run_id: str) -> list[ThemeTrack]:
    return [ThemeTrack(**t) for t in _load_json("themes.json", run_id)]


def load_chains(run_id: str) -> list[ChainLink]:
    return [ChainLink(**c) for c in _load_json("chains.json", run_id)]


def load_story(run_id: str) -> LifeStoryBook:
    return LifeStoryBook(**_load_json("story.json", run_id))


def load_selves(run_id: str) -> SelfVoiceMap:
    return SelfVoiceMap(**_load_json("selves.json", run_id))


def load_reframe_candidates(run_id: str) -> list[ReframeCandidate]:
    return [ReframeCandidate(**c) for c in _load_json("reframe_candidates.json", run_id)]
