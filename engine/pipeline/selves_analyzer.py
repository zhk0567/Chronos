from __future__ import annotations

import math
import uuid
from collections import Counter, defaultdict

from llm.ollama_client import make_evidence
from schemas.models import (
    EmotionPoint,
    EvidenceSource,
    InfoUnit,
    InfoUnitType,
    SelfVoiceMap,
    SelfVoiceProfile,
    StarLayoutPoint,
    VoiceTimelinePoint,
    VoiceTransition,
)

VOICE_KEYWORDS: dict[str, tuple[str, list[str]]] = {
    "critic": ("批评者", ["应该", "失败", "不够好", "批评", "自责", "糟糕", "不行"]),
    "comforter": ("安慰者", ["没关系", "可以", "休息", "接受", "理解", "温柔", "照顾"]),
    "dreamer": ("梦想家", ["希望", "未来", "想要", "梦想", "可能", "期待", "愿景"]),
    "observer": ("观察者", ["注意到", "发现", "看来", "也许", "思考", "观察", "意识到"]),
}

CLUSTER_MIN_UNITS = 8


def _unit_text(unit: InfoUnit) -> str:
    ta = unit.thought_anchor
    parts = [
        ta.self_voice if ta else None,
        ta.cognitive_pattern if ta else None,
        ta.core_concern if ta else None,
        unit.source_span.text if unit.source_span else None,
    ]
    return " ".join(filter(None, parts))


def _classify_voice(text: str) -> str:
    if not text:
        return "other"
    scores: dict[str, int] = {}
    for vtype, (_, keywords) in VOICE_KEYWORDS.items():
        scores[vtype] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"


def _label_cluster(texts: list[str]) -> str:
    combined = " ".join(texts)
    return _classify_voice(combined)


def _cluster_voice_types(units: list[InfoUnit]) -> dict[str, str]:
    """TF-IDF + KMeans 聚类；样本不足时回退关键词分类。"""
    if len(units) < CLUSTER_MIN_UNITS:
        return {u.id: _classify_voice(_unit_text(u)) for u in units}

    try:
        import jieba
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        return {u.id: _classify_voice(_unit_text(u)) for u in units}

    texts = [_unit_text(u) for u in units]
    stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "自己", "这"}

    def tokenizer(text: str) -> list[str]:
        return [w for w in jieba.cut(text) if len(w) >= 2 and w not in stopwords]

    vectorizer = TfidfVectorizer(tokenizer=tokenizer, max_features=300, min_df=1)
    matrix = vectorizer.fit_transform(texts)
    if matrix.shape[0] < 2:
        return {u.id: _classify_voice(_unit_text(u)) for u in units}

    n_clusters = min(4, max(2, len(units) // 4))
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(matrix)

    cluster_to_voice: dict[int, str] = {}
    for cid in range(n_clusters):
        cluster_texts = [texts[i] for i in range(len(texts)) if labels[i] == cid]
        cluster_to_voice[cid] = _label_cluster(cluster_texts)

    return {units[i].id: cluster_to_voice[labels[i]] for i in range(len(units))}


def analyze_selves(
    units: list[InfoUnit],
    emotion_series: list[EmotionPoint],
) -> SelfVoiceMap:
    thought_units = [u for u in units if u.unit_type == InfoUnitType.THOUGHT_ANCHOR]
    if not thought_units:
        return SelfVoiceMap()

    voice_by_unit = _cluster_voice_types(thought_units)
    by_voice: dict[str, list[InfoUnit]] = defaultdict(list)
    by_date_voice: dict[str, Counter] = defaultdict(Counter)

    for unit in thought_units:
        vtype = voice_by_unit.get(unit.id, "other")
        by_voice[vtype].append(unit)
        by_date_voice[unit.date][vtype] += 1

    profiles: list[SelfVoiceProfile] = []
    for vtype, vunits in by_voice.items():
        label = VOICE_KEYWORDS.get(vtype, ("其他", []))[0]
        quotes = []
        for u in vunits[:3]:
            if u.thought_anchor and u.thought_anchor.self_voice:
                quotes.append(u.thought_anchor.self_voice[:100])
            elif u.source_span.text:
                quotes.append(u.source_span.text[:100])

        method = "cluster" if len(thought_units) >= CLUSTER_MIN_UNITS else "keyword"
        profiles.append(
            SelfVoiceProfile(
                voiceType=vtype,
                label=label,
                description=f"在 {len(vunits)} 处内省记录中出现（{method}）",
                mentionCount=len(vunits),
                dates=sorted({u.date for u in vunits}),
                sampleQuotes=quotes,
                evidence=[
                    make_evidence(
                        u.date,
                        u.source_span.text[:100],
                        char_offset=u.source_span.char_offset,
                        source=EvidenceSource.EXPLICIT,
                    )
                    for u in vunits[:3]
                ],
            )
        )

    timeline: list[VoiceTimelinePoint] = []
    for date in sorted(by_date_voice.keys()):
        counts = by_date_voice[date]
        total = sum(counts.values()) or 1
        timeline.append(
            VoiceTimelinePoint(
                date=date,
                proportions={k: round(v / total, 3) for k, v in counts.items()},
            )
        )

    transitions: list[VoiceTransition] = []
    trans_counts: Counter[tuple[str, str]] = Counter()
    sorted_dates = sorted(by_date_voice.keys())
    for i in range(1, len(sorted_dates)):
        prev = by_date_voice[sorted_dates[i - 1]].most_common(1)
        curr = by_date_voice[sorted_dates[i]].most_common(1)
        if prev and curr and prev[0][0] != curr[0][0]:
            trans_counts[(prev[0][0], curr[0][0])] += 1

    for (fv, tv), count in trans_counts.most_common(5):
        fl = VOICE_KEYWORDS.get(fv, ("其他", []))[0]
        tl = VOICE_KEYWORDS.get(tv, ("其他", []))[0]
        transitions.append(
            VoiceTransition(
                fromVoice=fv,
                toVoice=tv,
                count=count,
                description=f"{fl} → {tl}（{count} 次）",
            )
        )

    star_layout = _build_star_layout(profiles)

    return SelfVoiceMap(
        profiles=profiles,
        timeline=timeline,
        transitions=transitions,
        starLayout=star_layout,
    )


def _build_star_layout(profiles: list[SelfVoiceProfile]) -> list[StarLayoutPoint]:
    if not profiles:
        return []
    n = len(profiles)
    layout: list[StarLayoutPoint] = []
    for i, p in enumerate(profiles):
        angle = 2 * math.pi * i / n
        layout.append(
            StarLayoutPoint(
                voiceType=p.voice_type,
                x=round(0.5 + 0.4 * math.cos(angle), 3),
                y=round(0.5 + 0.4 * math.sin(angle), 3),
            )
        )
    return layout
