from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from llm.ollama_client import OllamaClient
from llm.prompts.story import STORY_SYSTEM, STORY_USER
from schemas.models import (
    AnchorCard,
    ChainLink,
    EmotionPoint,
    LifeStoryBook,
    NarrativeLine,
    PersonNode,
    StoryNode,
    ThemeTrack,
)


def _load_story_edits(data_dir: Path, run_id: str) -> dict[str, dict]:
    path = data_dir / "story" / "edits" / f"{run_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_life_story(
    run_id: str,
    anchors: list[AnchorCard],
    chains: list[ChainLink],
    themes: list[ThemeTrack],
    relationships: list[PersonNode],
    emotion_series: list[EmotionPoint],
    data_dir: Path,
    llm: OllamaClient | None = None,
    use_llm: bool = False,
) -> LifeStoryBook:
    emotion_by_date = {p.date: p.score for p in emotion_series}
    anchor_by_id = {a.id: a for a in anchors}
    edits = _load_story_edits(data_dir, run_id)
    lines: list[NarrativeLine] = []
    seen_anchor_sets: set[frozenset] = set()

    for chain in chains:
        if chain.type not in ("theme", "person", "evolution") or len(chain.anchor_ids) < 2:
            continue
        key = frozenset(chain.anchor_ids)
        if key in seen_anchor_sets:
            continue
        seen_anchor_sets.add(key)

        chain_anchors = [anchor_by_id[aid] for aid in chain.anchor_ids if aid in anchor_by_id]
        if len(chain_anchors) < 2:
            continue

        theme_or_relation = chain.description.split("：")[0] if "：" in chain.description else chain.description
        nodes_payload = []
        for a in chain_anchors:
            ev_text = a.evidence[0].text if a.evidence else a.description
            nodes_payload.append({
                "anchorId": a.id,
                "date": a.date,
                "title": a.title,
                "evidence": ev_text[:200],
            })

        title = theme_or_relation
        tone_shift = None
        node_summaries: dict[str, str] = {}

        if use_llm and llm:
            try:
                user = STORY_USER.format(
                    theme_or_relation=theme_or_relation,
                    nodes_json=json.dumps(nodes_payload, ensure_ascii=False),
                )
                data = llm.chat_json(STORY_SYSTEM, user)
                title = data.get("title", title)
                tone_shift = data.get("toneShift")
                for n in data.get("nodes", []):
                    node_summaries[n.get("anchorId", "")] = n.get("summary", "")
            except Exception:
                pass

        story_nodes: list[StoryNode] = []
        arc: list[float] = []
        for a in chain_anchors:
            score = emotion_by_date.get(a.date)
            summary = node_summaries.get(a.id) or (
                a.evidence[0].text[:80] if a.evidence else "此处日记未记录细节"
            )
            story_nodes.append(
                StoryNode(
                    anchorId=a.id,
                    date=a.date,
                    title=a.title,
                    emotionScore=score,
                    summary=summary,
                )
            )
            if score is not None:
                arc.append(score)

        line_id = hashlib.md5(",".join(sorted(chain.anchor_ids)).encode()).hexdigest()[:8]
        edit = edits.get(line_id, {})
        lines.append(
            NarrativeLine(
                id=line_id,
                title=title,
                themeOrRelation=theme_or_relation,
                nodes=story_nodes,
                emotionArc=arc,
                toneShift=tone_shift,
                status=edit.get("status", "auto"),
                userNote=edit.get("userNote"),
            )
        )
        if len(lines) >= 10:
            break

    if not lines and len(anchors) >= 2:
        sorted_a = sorted(anchors, key=lambda a: a.date)[:5]
        story_nodes = [
            StoryNode(
                anchorId=a.id,
                date=a.date,
                title=a.title,
                emotionScore=emotion_by_date.get(a.date),
                summary=a.evidence[0].text[:80] if a.evidence else a.description[:80],
            )
            for a in sorted_a
        ]
        lines.append(
            NarrativeLine(
                id=str(uuid.uuid4())[:8],
                title="时间线上的关键锚点",
                themeOrRelation="综合叙事",
                nodes=story_nodes,
                emotionArc=[emotion_by_date.get(a.date, 0) for a in sorted_a],
            )
        )

    return LifeStoryBook(
        runId=run_id,
        lines=lines,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )
