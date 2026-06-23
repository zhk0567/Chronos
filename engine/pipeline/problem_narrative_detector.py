from __future__ import annotations

import json
import re
import uuid
from collections import Counter

from llm.ollama_client import OllamaClient, make_evidence
from llm.prompts.story import REFRAME_DETECT_SYSTEM, REFRAME_DETECT_USER
from schemas.models import (
    DiaryEntry,
    EmotionPoint,
    EvidenceSource,
    FactorConclusion,
    ReframeCandidate,
)

PROBLEM_PATTERNS = [
    re.compile(r"我总是.+"),
    re.compile(r"我是.+的人"),
    re.compile(r"我没办法.+"),
    re.compile(r"我不行"),
    re.compile(r"我注定.+"),
]

TURNING_KEYWORDS = ("但是", "然而", "没想到", "反而", "却", "幸好", "后来")


def detect_problem_narratives(
    entries: list[DiaryEntry],
    emotion_series: list[EmotionPoint],
    damaging: list[FactorConclusion],
    llm: OllamaClient | None = None,
    use_llm: bool = False,
) -> list[ReframeCandidate]:
    emotion_by_date = {p.date: p.score for p in emotion_series}
    avg_emotion = sum(emotion_by_date.values()) / len(emotion_by_date) if emotion_by_date else 5.0
    statement_counts: Counter[str] = Counter()

    for entry in entries:
        for pat in PROBLEM_PATTERNS:
            for m in pat.finditer(entry.content):
                stmt = m.group(0).strip()[:80]
                if len(stmt) >= 4:
                    statement_counts[stmt] += 1

    for factor in damaging:
        for ev in factor.evidence:
            if any(kw in ev.text for kw in ("总是", "我是", "没办法")):
                statement_counts[ev.text[:80]] += 1

    candidates: list[ReframeCandidate] = []
    for stmt, freq in statement_counts.most_common(8):
        if freq < 2:
            continue
        exceptions = _find_exceptions(stmt, entries, emotion_by_date, avg_emotion)
        candidates.append(
            ReframeCandidate(
                id=str(uuid.uuid4())[:8],
                problemStatement=stmt,
                internalizedPattern=_infer_pattern(stmt),
                frequency=freq,
                exceptionMoments=exceptions,
                relatedAnchorIds=[],
            )
        )

    if use_llm and llm and len(candidates) < 3:
        try:
            excerpts = [{"date": e.date, "text": e.content[:300]} for e in entries[:30]]
            user = REFRAME_DETECT_USER.format(entries_json=json.dumps(excerpts, ensure_ascii=False))
            data = llm.chat_json(REFRAME_DETECT_SYSTEM, user)
            for raw in data.get("candidates", []):
                stmt = raw.get("problemStatement", "")
                if not stmt or any(c.problem_statement == stmt for c in candidates):
                    continue
                exceptions = _find_exceptions(stmt, entries, emotion_by_date, avg_emotion)
                candidates.append(
                    ReframeCandidate(
                        id=str(uuid.uuid4())[:8],
                        problemStatement=stmt,
                        internalizedPattern=raw.get("internalizedPattern", "内化叙事"),
                        frequency=len(raw.get("relatedDates", [])) or 2,
                        exceptionMoments=exceptions,
                        relatedAnchorIds=[],
                    )
                )
        except Exception:
            pass

    return candidates[:5]


def _infer_pattern(stmt: str) -> str:
    if "总是" in stmt:
        return "绝对化自我标签"
    if "我是" in stmt:
        return "本质化自我定义"
    if "没办法" in stmt or "不行" in stmt:
        return "无力感叙事"
    return "重复问题叙事"


def _find_exceptions(
    stmt: str,
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
    avg_emotion: float,
) -> list:
    exceptions = []
    keywords = set(stmt.replace("我", "").replace("总是", "")[:10])
    for entry in entries:
        score = emotion_by_date.get(entry.date, avg_emotion)
        has_turning = any(kw in entry.content for kw in TURNING_KEYWORDS)
        high_mood = score > avg_emotion + 1
        if has_turning or high_mood:
            if keywords and not any(k in entry.content for k in keywords if len(k) >= 2):
                exceptions.append(
                    make_evidence(
                        entry.date,
                        entry.content[:150],
                        source=EvidenceSource.EXPLICIT,
                    )
                )
            elif high_mood:
                exceptions.append(
                    make_evidence(
                        entry.date,
                        entry.content[:150],
                        source=EvidenceSource.EXPLICIT,
                    )
                )
        if len(exceptions) >= 3:
            break
    return exceptions
