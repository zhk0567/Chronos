from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class MetricScore:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass
class BenchmarkResult:
    name: str
    entry_count: int
    ran_at: str
    anchor: MetricScore
    theme: MetricScore
    relationship: MetricScore
    warning: MetricScore | None = None
    details: dict = field(default_factory=dict)


def _prf(tp: int, fp: int, fn: int) -> MetricScore:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return MetricScore(precision=round(precision, 3), recall=round(recall, 3), f1=round(f1, 3), tp=tp, fp=fp, fn=fn)


def _anchor_matches(pred, label: dict, date_slack_days: int = 3) -> bool:
    if pred.emergence_type.value != label.get("emergenceType"):
        return False
    needle = label.get("titleContains", "")
    if needle and needle not in pred.title and needle not in pred.description:
        return False
    expected_date = label.get("date")
    if expected_date:
        from datetime import datetime

        pred_dt = datetime.strptime(pred.date, "%Y-%m-%d")
        exp_dt = datetime.strptime(expected_date, "%Y-%m-%d")
        if abs((pred_dt - exp_dt).days) > date_slack_days:
            return False
    return True


def _match_labels(items: list, labels: list[dict], matcher) -> MetricScore:
    if not labels:
        return _prf(0, len(items), 0)
    matched_preds: set[int] = set()
    matched_labels: set[int] = set()
    for li, label in enumerate(labels):
        for pi, pred in enumerate(items):
            if pi in matched_preds:
                continue
            if matcher(pred, label):
                matched_preds.add(pi)
                matched_labels.add(li)
                break
    tp = len(matched_labels)
    fp = len(items) - len(matched_preds)
    fn = len(labels) - tp
    return _prf(tp, fp, fn)


def _warning_matches(pred, label: dict) -> bool:
    needles = label.get("signalsContains", [])
    if not needles:
        return False
    return all(any(needle in signal for signal in pred.signals) for needle in needles)


def run_benchmark(
    entries: list,
    labels: dict,
    use_llm: bool = False,
    contexts: list | None = None,
) -> BenchmarkResult:
    from pipeline.anchor_detector import detect_anchors
    from pipeline.emotion_analyzer import score_emotions
    from pipeline.morph_classifier import extract_all_morph_and_units
    from pipeline.network_analyzer import analyze_network
    from pipeline.theme_analyzer import analyze_themes
    from pipeline.warning_detector import detect_warning_patterns
    from schemas.models import DailyContext, DiaryEntry

    diary = [DiaryEntry(**e) if isinstance(e, dict) else e for e in entries]

    morphs, units = extract_all_morph_and_units(diary, None, use_llm=False, batch_size=20)
    emotion = score_emotions(diary, None, use_llm=False)
    anchors = detect_anchors(diary, morphs, units, emotion)
    themes = analyze_themes(diary, emotion, None, use_llm=False)
    relationships = analyze_network(units, emotion)

    anchor_metric = _match_labels(anchors, labels.get("anchors", []), _anchor_matches)

    def theme_matcher(track, label: dict) -> bool:
        kw = label.get("keyword", "")
        if not kw:
            return False
        if kw not in track.theme:
            return False
        min_m = label.get("minMentions", 1)
        return len(track.intensity_curve) >= min_m

    theme_metric = _match_labels(themes, labels.get("themes", []), theme_matcher)

    def rel_matcher(node, label: dict) -> bool:
        needle = label.get("nameContains", "")
        if not needle:
            return False
        if needle not in node.name:
            return False
        return node.mention_count >= label.get("minMentions", 1)

    rel_metric = _match_labels(relationships, labels.get("relationships", []), rel_matcher)

    warning_labels = labels.get("warnings", [])
    warning_metric: MetricScore | None = None
    warnings_found = 0
    if warning_labels and contexts:
        ctx_models = [DailyContext(**c) if isinstance(c, dict) else c for c in contexts]
        warnings = detect_warning_patterns(ctx_models, emotion)
        warnings_found = len(warnings)
        warning_metric = _match_labels(warnings, warning_labels, _warning_matches)

    details: dict = {
        "anchorsFound": len(anchors),
        "themesFound": len(themes),
        "relationshipsFound": len(relationships),
    }
    if warning_metric is not None:
        from benchmark.targets import WARNING_PRECISION_TARGET, WARNING_RECALL_TARGET, warning_targets_met

        details["warningsFound"] = warnings_found
        details["warningTargets"] = {
            "recall": WARNING_RECALL_TARGET,
            "precision": WARNING_PRECISION_TARGET,
            "met": warning_targets_met(warning_metric.precision, warning_metric.recall),
        }

    return BenchmarkResult(
        name=labels.get("name", "unnamed"),
        entry_count=len(diary),
        ran_at=datetime.now(timezone.utc).isoformat(),
        anchor=anchor_metric,
        theme=theme_metric,
        relationship=rel_metric,
        warning=warning_metric,
        details=details,
    )


def load_fixture(name: str = "demo") -> tuple[list, dict, list | None]:
    base = Path(__file__).parent / "fixtures"
    entries = json.loads((base / f"{name}_entries.json").read_text(encoding="utf-8"))
    labels = json.loads((base / f"{name}_labels.json").read_text(encoding="utf-8"))
    context_path = base / f"{name}_context.json"
    contexts = json.loads(context_path.read_text(encoding="utf-8")) if context_path.exists() else None
    return entries, labels, contexts


def list_fixture_names() -> list[str]:
    base = Path(__file__).parent / "fixtures"
    names: set[str] = set()
    for path in base.glob("*_entries.json"):
        names.add(path.stem.replace("_entries", ""))
    return sorted(names)


def run_all_benchmarks(use_llm: bool = False) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for name in list_fixture_names():
        entries, labels, contexts = load_fixture(name)
        results.append(run_benchmark(entries, labels, use_llm=use_llm, contexts=contexts))
    return results


def result_to_dict(result: BenchmarkResult) -> dict:
    def m(s: MetricScore) -> dict:
        return {"precision": s.precision, "recall": s.recall, "f1": s.f1, "tp": s.tp, "fp": s.fp, "fn": s.fn}

    payload = {
        "name": result.name,
        "entryCount": result.entry_count,
        "ranAt": result.ran_at,
        "anchor": m(result.anchor),
        "theme": m(result.theme),
        "relationship": m(result.relationship),
        "details": result.details,
    }
    if result.warning is not None:
        payload["warning"] = m(result.warning)
    return payload
