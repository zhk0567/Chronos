from __future__ import annotations

import json
import uuid
from collections import defaultdict

from llm.ollama_client import OllamaClient, make_evidence
from llm.prompts.extract import THEME_SYSTEM, THEME_USER
from schemas.models import DiaryEntry, EmotionPoint, EvidenceSource, ThemeIntensityPoint, ThemeTrack

_THEME_STOPWORDS = frozenset(
    {
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
        "自己", "这", "今天", "明天", "昨天", "然后", "但是", "因为", "所以",
    }
)


def _theme_tokenizer(text: str) -> list[str]:
    import jieba

    return [w for w in jieba.cut(text) if len(w) >= 2 and w not in _THEME_STOPWORDS]


def _doc_term_matrix(entries: list[DiaryEntry], min_df: int = 2):
    from sklearn.feature_extraction.text import CountVectorizer

    docs = [e.content for e in entries]
    vectorizer = CountVectorizer(tokenizer=_theme_tokenizer, max_features=400, min_df=min_df)
    matrix = vectorizer.fit_transform(docs)
    return matrix, vectorizer


def analyze_themes(
    entries: list[DiaryEntry],
    emotion_series: list[EmotionPoint],
    llm: OllamaClient,
    use_llm: bool = True,
) -> list[ThemeTrack]:
    emotion_by_date = {p.date: p.score for p in emotion_series}

    if use_llm and len(entries) >= 3:
        try:
            sample = entries
            if len(entries) > 60:
                step = max(1, len(entries) // 60)
                sample = entries[::step][:60]
            summaries = [{"date": e.date, "text": e.content[:150]} for e in sample]
            user = THEME_USER.format(summaries_json=json.dumps(summaries, ensure_ascii=False))
            data = llm.chat_json(THEME_SYSTEM, user)
            tracks = []
            for raw in data.get("themes", []):
                theme = raw.get("theme", "")
                dates = raw.get("dates", [])
                if not theme or not dates:
                    continue
                curve = _build_intensity_curve(theme, dates, entries, emotion_by_date)
                framework_shift = None
                early = raw.get("frameworkEarly")
                late = raw.get("frameworkLate")
                if early and late and early != late:
                    framework_shift = f"从「{early}」转向「{late}」"

                tracks.append(
                    ThemeTrack(
                        theme=theme,
                        firstSeen=min(dates),
                        lastSeen=max(dates),
                        peakDate=_peak_date(curve),
                        intensityCurve=curve,
                        frameworkShift=framework_shift,
                        evidence=[
                            make_evidence(
                                d,
                                next((e.content[:100] for e in entries if e.date == d), ""),
                                source=EvidenceSource.INFERRED,
                            )
                            for d in sorted(dates)[:3]
                        ],
                    )
                )
            if tracks:
                return tracks
        except Exception:
            pass

    nmf_tracks = _nmf_themes(entries, emotion_by_date)
    if nmf_tracks:
        return nmf_tracks

    lda_tracks = _lda_themes(entries, emotion_by_date)
    if lda_tracks:
        return lda_tracks

    bertopic_tracks = _bertopic_themes(entries, emotion_by_date)
    if bertopic_tracks:
        return bertopic_tracks

    return _heuristic_themes(entries, emotion_by_date)


def _matrix_themes(
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
    doc_topics,
    components,
    feature_names,
    prefix: str,
    prob_threshold: float = 0.25,
    min_dates: int = 3,
) -> list[ThemeTrack]:
    n_topics = components.shape[0]
    tracks: list[ThemeTrack] = []

    for topic_idx in range(n_topics):
        top_idx = components[topic_idx].argsort()[-3:][::-1]
        keywords = [feature_names[i] for i in top_idx if components[topic_idx][i] > 0]
        if not keywords:
            continue
        theme = "·".join(keywords[:2])
        dates = [
            entries[i].date
            for i in range(len(entries))
            if doc_topics[i, topic_idx] >= prob_threshold
        ]
        if len(dates) < min_dates:
            continue
        dates = sorted(set(dates))
        curve = _build_intensity_curve(theme, dates, entries, emotion_by_date)
        tracks.append(
            ThemeTrack(
                theme=f"[{prefix}] {theme}",
                firstSeen=dates[0],
                lastSeen=dates[-1],
                peakDate=_peak_date(curve),
                intensityCurve=curve,
                evidence=[
                    make_evidence(d, keywords[0], source=EvidenceSource.INFERRED) for d in dates[:2]
                ],
            )
        )
    return tracks


def _nmf_themes(
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeTrack]:
    if len(entries) < 10:
        return []
    try:
        from sklearn.decomposition import NMF
    except ImportError:
        return []

    matrix, vectorizer = _doc_term_matrix(entries)
    if matrix.shape[1] < 3:
        return []

    n_topics = min(8, max(2, len(entries) // 12))
    nmf = NMF(n_components=n_topics, random_state=42, max_iter=300)
    doc_topics = nmf.fit_transform(matrix)
    features = vectorizer.get_feature_names_out()
    assignments = doc_topics.argmax(axis=1)
    tracks: list[ThemeTrack] = []

    for topic_idx in range(n_topics):
        top_idx = nmf.components_[topic_idx].argsort()[-3:][::-1]
        keywords = [features[i] for i in top_idx if nmf.components_[topic_idx][i] > 0]
        if not keywords:
            continue
        theme = "·".join(keywords[:2])
        dates = sorted({entries[i].date for i in range(len(entries)) if assignments[i] == topic_idx})
        if len(dates) < 3:
            continue
        curve = _build_intensity_curve(theme, dates, entries, emotion_by_date)
        tracks.append(
            ThemeTrack(
                theme=f"[NMF] {theme}",
                firstSeen=dates[0],
                lastSeen=dates[-1],
                peakDate=_peak_date(curve),
                intensityCurve=curve,
                evidence=[
                    make_evidence(d, keywords[0], source=EvidenceSource.INFERRED) for d in dates[:2]
                ],
            )
        )
    return tracks


def _lda_themes(
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeTrack]:
    if len(entries) < 10:
        return []
    try:
        from sklearn.decomposition import LatentDirichletAllocation
    except ImportError:
        return []

    matrix, vectorizer = _doc_term_matrix(entries)
    if matrix.shape[1] < 3:
        return []

    n_topics = min(8, max(2, len(entries) // 12))
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=20,
        learning_method="online",
    )
    doc_topics = lda.fit_transform(matrix)
    return _matrix_themes(
        entries,
        emotion_by_date,
        doc_topics,
        lda.components_,
        vectorizer.get_feature_names_out(),
        "LDA",
    )


def _bertopic_themes(
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeTrack]:
    """可选 BERTopic 主题建模（需 `pip install bertopic`）。未安装或失败时返回空列表。"""
    if len(entries) < 15:
        return []
    try:
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer
    except ImportError:
        return []

    docs = [e.content for e in entries]
    try:
        vectorizer = CountVectorizer(tokenizer=_theme_tokenizer, max_features=400, min_df=2)
        topic_model = BERTopic(
            vectorizer_model=vectorizer,
            min_topic_size=max(3, len(entries) // 12),
            calculate_probabilities=True,
            verbose=False,
        )
        topics, _probs = topic_model.fit_transform(docs)
    except Exception:
        return []

    tracks: list[ThemeTrack] = []
    for topic_id in sorted({t for t in topics if t != -1}):
        topic_words = topic_model.get_topic(topic_id)
        if not topic_words:
            continue
        keywords = [w for w, _ in topic_words[:3] if w]
        if not keywords:
            continue
        theme = "·".join(keywords[:2])
        dates = sorted({entries[i].date for i, t in enumerate(topics) if t == topic_id})
        if len(dates) < 3:
            continue
        curve = _build_intensity_curve(theme, dates, entries, emotion_by_date)
        tracks.append(
            ThemeTrack(
                theme=f"[BERTopic] {theme}",
                firstSeen=dates[0],
                lastSeen=dates[-1],
                peakDate=_peak_date(curve),
                intensityCurve=curve,
                evidence=[
                    make_evidence(d, keywords[0], source=EvidenceSource.INFERRED) for d in dates[:2]
                ],
            )
        )
    return tracks


def _build_intensity_curve(
    theme: str,
    dates: list[str],
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeIntensityPoint]:
    curve: list[ThemeIntensityPoint] = []
    for entry in entries:
        count = entry.content.count(theme)
        if theme not in entry.content and count == 0:
            # fuzzy: check if any word from theme appears
            count = sum(1 for ch in theme if ch in entry.content) // max(1, len(theme))
        if count > 0 or entry.date in dates:
            emotion_weight = emotion_by_date.get(entry.date, 5.0) / 10.0
            intensity = count * (0.5 + emotion_weight)
            curve.append(ThemeIntensityPoint(date=entry.date, intensity=round(intensity, 2)))
    return curve


def _peak_date(curve: list[ThemeIntensityPoint]) -> str | None:
    if not curve:
        return None
    return max(curve, key=lambda p: p.intensity).date


def _heuristic_themes(
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeTrack]:
    import jieba
    from collections import Counter

    word_counts: Counter[str] = Counter()
    word_dates: dict[str, list[str]] = defaultdict(list)

    stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "今天", "明天", "昨天"}

    for entry in entries:
        words = [w for w in jieba.cut(entry.content) if len(w) >= 2 and w not in stopwords]
        for w in set(words):
            word_counts[w] += 1
            word_dates[w].append(entry.date)

    tracks: list[ThemeTrack] = []
    for word, count in word_counts.most_common(8):
        if count < 3:
            continue
        dates = sorted(set(word_dates[word]))
        curve = _build_intensity_curve(word, dates, entries, emotion_by_date)
        tracks.append(
            ThemeTrack(
                theme=word,
                firstSeen=dates[0],
                lastSeen=dates[-1],
                peakDate=_peak_date(curve),
                intensityCurve=curve,
                evidence=[
                    make_evidence(d, word, source=EvidenceSource.INFERRED) for d in dates[:2]
                ],
            )
        )
    return tracks
