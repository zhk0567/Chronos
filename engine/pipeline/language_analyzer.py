from __future__ import annotations

import json
from pathlib import Path

import jieba
import numpy as np

from llm.ollama_client import OllamaClient, make_evidence
from llm.prompts.extract import METAPHOR_SYSTEM, METAPHOR_USER
from schemas.models import DiaryEntry, EvidenceSource, LanguageMetric


def _load_lexicon(name: str) -> set[str]:
    path = Path(__file__).parent.parent / "data" / "lexicons" / f"{name}.txt"
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


LEXICON_NAMES = {
    "pronouns": "代词使用",
    "cognitive": "认知加工词",
    "temporal": "时间取向词",
    "absolutist": "绝对化语言",
}


def analyze_language(
    entries: list[DiaryEntry],
    llm: OllamaClient | None = None,
    use_llm: bool = True,
) -> list[LanguageMetric]:
    if len(entries) < 3:
        return [
            LanguageMetric(
                name="语言模式",
                trend="insufficient_data",
                confidence=0.2,
                description="日记数量不足，无法进行语言模式分析",
                evidence=[],
            )
        ]

    metrics: list[LanguageMetric] = []
    for lex_key, label in LEXICON_NAMES.items():
        words = _load_lexicon(lex_key)
        if not words:
            continue
        metric = _compute_lexicon_trend(entries, words, label)
        if metric:
            metrics.append(metric)

    if llm and use_llm:
        try:
            batch = [{"date": e.date, "content": e.content[:300]} for e in entries[-20:]]
            user = METAPHOR_USER.format(entries_json=json.dumps(batch, ensure_ascii=False))
            data = llm.chat_json(METAPHOR_SYSTEM, user)
            metaphors = data.get("metaphors", [])
            if metaphors:
                types = [m.get("type", "其他") for m in metaphors]
                dominant = max(set(types), key=types.count)
                metrics.append(
                    LanguageMetric(
                        name="隐喻类型",
                        trend="stable",
                        confidence=0.5,
                        description=f"常见隐喻类型：{dominant}（共 {len(metaphors)} 处）",
                        evidence=[
                            make_evidence(
                                m.get("date", entries[-1].date),
                                m.get("metaphor", "")[:80],
                                source=EvidenceSource.EXPLICIT,
                            )
                            for m in metaphors[:3]
                        ],
                    )
                )
        except Exception:
            pass

    return metrics


def _compute_lexicon_trend(
    entries: list[DiaryEntry],
    lexicon: set[str],
    label: str,
) -> LanguageMetric | None:
    ratios: list[float] = []
    for entry in entries:
        tokens = list(jieba.cut(entry.content))
        if not tokens:
            continue
        hits = sum(1 for t in tokens if t in lexicon)
        ratios.append(hits / len(tokens))

    if len(ratios) < 3:
        return None

    mid = len(ratios) // 2
    early = float(np.mean(ratios[:mid]))
    late = float(np.mean(ratios[mid:]))
    change = ((late - early) / max(early, 0.001)) * 100

    if late > early * 1.15:
        trend = "increasing"
    elif late < early * 0.85:
        trend = "decreasing"
    else:
        trend = "stable"

    return LanguageMetric(
        name=label,
        trend=trend,
        currentRatio=round(late, 4),
        changePercent=round(change, 1),
        confidence=0.55 if len(entries) >= 10 else 0.4,
        description=f"{label}比例从 {early:.3f} 变为 {late:.3f}（变化 {change:+.1f}%）",
        evidence=[
            make_evidence(
                entries[-1].date,
                entries[-1].content[:80],
                source=EvidenceSource.INFERRED,
            )
        ],
    )
