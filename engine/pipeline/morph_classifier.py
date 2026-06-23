from __future__ import annotations

import uuid
from typing import Callable, Optional

from llm.ollama_client import OllamaClient
from llm.prompts.extract import EXTRACT_SYSTEM, EXTRACT_USER, EXTRACT_BATCH_SYSTEM, EXTRACT_BATCH_USER
from schemas.models import (
    DiaryEntry,
    DiaryParagraph,
    EmotionMarker,
    EventPackage,
    InfoUnit,
    InfoUnitType,
    MorphResult,
    MorphType,
    RhythmInfo,
    SourceSpan,
    ThoughtAnchor,
)


def _split_paragraphs(content: str) -> list[DiaryParagraph]:
    blocks = content.split("\n\n")
    paragraphs: list[DiaryParagraph] = []
    offset = 0
    for block in blocks:
        text = block.strip()
        if not text:
            offset += len(block) + 2
            continue
        idx = content.find(text, offset)
        paragraphs.append(
            DiaryParagraph(index=len(paragraphs), text=text, charOffset=idx if idx >= 0 else offset)
        )
        offset = (idx if idx >= 0 else offset) + len(text) + 2
    if not paragraphs and content.strip():
        paragraphs.append(DiaryParagraph(index=0, text=content.strip(), charOffset=0))
    return paragraphs


def ensure_paragraphs(entry: DiaryEntry) -> DiaryEntry:
    if entry.paragraphs:
        return entry
    return entry.model_copy(update={"paragraphs": _split_paragraphs(entry.content)})


def extract_morph_and_units(
    entry: DiaryEntry,
    llm: OllamaClient,
    use_llm: bool = True,
) -> tuple[list[MorphResult], list[InfoUnit]]:
    morphs, units = extract_all_morph_and_units([entry], llm, use_llm, batch_size=1)
    return morphs, units


def extract_all_morph_and_units(
    entries: list[DiaryEntry],
    llm: OllamaClient,
    use_llm: bool = True,
    batch_size: int = 12,
    on_batch: Optional[Callable[[int, int], None]] = None,
) -> tuple[list[MorphResult], list[InfoUnit]]:
    """Batch LLM extract to avoid N sequential API calls."""
    all_morphs: list[MorphResult] = []
    all_units: list[InfoUnit] = []
    prepared = [ensure_paragraphs(e) for e in entries]
    total_batches = (len(prepared) + batch_size - 1) // batch_size if prepared else 0

    for batch_idx, start in enumerate(range(0, len(prepared), batch_size)):
        batch = prepared[start : start + batch_size]
        if on_batch:
            on_batch(batch_idx + 1, total_batches)

        if use_llm and batch:
            try:
                payload = []
                for entry in batch:
                    payload.append({
                        "date": entry.date,
                        "paragraphs": [{"index": p.index, "text": p.text[:250]} for p in entry.paragraphs],
                    })
                user = EXTRACT_BATCH_USER.format(
                    count=len(batch),
                    entries_json=__import__("json").dumps(payload, ensure_ascii=False),
                )
                data = llm.chat_json(EXTRACT_BATCH_SYSTEM, user)
                parsed = _parse_batch_response(data, batch)
                if parsed:
                    m, u = parsed
                    all_morphs.extend(m)
                    all_units.extend(u)
                    continue
            except Exception:
                pass

        for entry in batch:
            m, u = _heuristic_extract(entry)
            all_morphs.extend(m)
            all_units.extend(u)

    return all_morphs, all_units


def _parse_batch_response(
    data: dict,
    batch: list[DiaryEntry],
) -> Optional[tuple[list[MorphResult], list[InfoUnit]]]:
    by_date = {e.date: e for e in batch}
    morphs: list[MorphResult] = []
    units: list[InfoUnit] = []

    for entry_data in data.get("entries", []):
        date = entry_data.get("date", "")
        entry = by_date.get(date)
        if not entry:
            continue
        for para in entry_data.get("paragraphs", []):
            pidx = para.get("paragraphIndex", 0)
            mtype = _parse_morph(para.get("morphType", "mixed"))
            conf = float(para.get("confidence", 0.7))
            morphs.append(MorphResult(date=date, paragraphIndex=pidx, type=mtype, confidence=conf))
            para_text = next((p.text for p in entry.paragraphs if p.index == pidx), "")
            para_offset = next((p.char_offset for p in entry.paragraphs if p.index == pidx), 0)
            for u in para.get("units", []):
                unit = _build_unit(date, pidx, para_text, para_offset, mtype, u)
                if unit:
                    units.append(unit)

    if not morphs:
        return None
    return morphs, units


def _parse_morph(raw: str) -> MorphType:
    mapping = {
        "narrative": MorphType.NARRATIVE,
        "introspective": MorphType.INTROSPECTIVE,
        "sketch": MorphType.SKETCH,
        "list": MorphType.LIST,
        "mixed": MorphType.MIXED,
    }
    return mapping.get(raw, MorphType.MIXED)


def _build_unit(
    date: str,
    pidx: int,
    text: str,
    offset: int,
    mtype: MorphType,
    raw: dict,
) -> Optional[InfoUnit]:
    utype = raw.get("unitType", "")
    type_map = {
        "event_package": InfoUnitType.EVENT_PACKAGE,
        "thought_anchor": InfoUnitType.THOUGHT_ANCHOR,
        "emotion_marker": InfoUnitType.EMOTION_MARKER,
        "rhythm_info": InfoUnitType.RHYTHM_INFO,
    }
    unit_type = type_map.get(utype)
    if not unit_type:
        return None

    span = SourceSpan(
        date=date,
        paragraphIndex=pidx,
        charOffset=offset,
        charLength=len(text),
        text=text[:300],
    )

    ep = raw.get("eventPackage") or {}
    ta = raw.get("thoughtAnchor") or {}
    em = raw.get("emotionMarker") or {}
    ri = raw.get("rhythmInfo") or {}

    return InfoUnit(
        id=str(uuid.uuid4())[:8],
        date=date,
        unitType=unit_type,
        morphType=mtype,
        sourceSpan=span,
        eventPackage=EventPackage(**ep) if unit_type == InfoUnitType.EVENT_PACKAGE else None,
        thoughtAnchor=ThoughtAnchor(**ta) if unit_type == InfoUnitType.THOUGHT_ANCHOR else None,
        emotionMarker=EmotionMarker(**em) if unit_type == InfoUnitType.EMOTION_MARKER else None,
        rhythmInfo=RhythmInfo(**ri) if unit_type == InfoUnitType.RHYTHM_INFO else None,
    )


def _heuristic_extract(entry: DiaryEntry) -> tuple[list[MorphResult], list[InfoUnit]]:
    entry = ensure_paragraphs(entry)
    morphs: list[MorphResult] = []
    units: list[InfoUnit] = []

    for p in entry.paragraphs:
        mtype, conf = _classify_heuristic(p.text)
        morphs.append(MorphResult(date=entry.date, paragraphIndex=p.index, type=mtype, confidence=conf))
        unit = _heuristic_unit(entry.date, p, mtype)
        units.append(unit)

    return morphs, units


def _classify_heuristic(text: str) -> tuple[MorphType, float]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) >= 3 and all(len(l) < 30 for l in lines):
        if any(l.startswith(("-", "•", "1.", "2.", "①")) for l in lines):
            return MorphType.LIST, 0.6
    if len(text) < 80:
        return MorphType.SKETCH, 0.5
    introspective_kw = ["觉得", "认为", "反思", "意识到", "为什么", "也许", "可能", "自己"]
    narrative_kw = ["今天", "昨天", "去了", "发生", "见到", "一起"]
    i_score = sum(1 for k in introspective_kw if k in text)
    n_score = sum(1 for k in narrative_kw if k in text)
    if i_score > n_score and i_score >= 2:
        return MorphType.INTROSPECTIVE, 0.55
    if n_score >= 2:
        return MorphType.NARRATIVE, 0.55
    return MorphType.MIXED, 0.4


def _heuristic_unit(date: str, para: DiaryParagraph, mtype: MorphType) -> InfoUnit:
    span = SourceSpan(
        date=date,
        paragraphIndex=para.index,
        charOffset=para.char_offset,
        charLength=len(para.text),
        text=para.text[:300],
    )
    uid = str(uuid.uuid4())[:8]

    if mtype == MorphType.NARRATIVE:
        return InfoUnit(
            id=uid,
            date=date,
            unitType=InfoUnitType.EVENT_PACKAGE,
            morphType=mtype,
            sourceSpan=span,
            eventPackage=EventPackage(summary=para.text[:100]),
        )
    if mtype == MorphType.INTROSPECTIVE:
        return InfoUnit(
            id=uid,
            date=date,
            unitType=InfoUnitType.THOUGHT_ANCHOR,
            morphType=mtype,
            sourceSpan=span,
            thoughtAnchor=ThoughtAnchor(coreConcern=para.text[:80]),
        )
    if mtype == MorphType.LIST:
        items = [l.strip() for l in para.text.split("\n") if l.strip()]
        return InfoUnit(
            id=uid,
            date=date,
            unitType=InfoUnitType.RHYTHM_INFO,
            morphType=mtype,
            sourceSpan=span,
            rhythmInfo=RhythmInfo(items=items[:10]),
        )
    return InfoUnit(
        id=uid,
        date=date,
        unitType=InfoUnitType.EMOTION_MARKER,
        morphType=mtype,
        sourceSpan=span,
        emotionMarker=EmotionMarker(label="未标注", intensity=5.0),
    )
