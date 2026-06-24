from __future__ import annotations

import html
import json
import uuid
from datetime import datetime, timezone

from schemas.models import (
    AnchorCard,
    ChainLink,
    DailyContext,
    FactorConclusion,
    InsightReport,
    InteractionEffect,
    LanguageMetric,
    LifeStoryBook,
    PersonNode,
    PhysioCoupling,
    ReframeCandidate,
    ReportConclusion,
    ReportSection,
    SelfVoiceMap,
    SpaceEmotionLink,
    StabilityMetric,
    ThemeTrack,
    WarningPattern,
    WeatherInsight,
    WeatherSensitivity,
)
from utils.interpretation import (
    clean_factor_statement,
    factor_implication,
    format_controlled_for,
    LANGUAGE_TREND_LABELS,
    TONE_TREND_LABELS,
)


def build_report(
    run_id: str,
    entry_count: int,
    date_range: dict[str, str],
    anchors: list[AnchorCard],
    emotion_series: list,
    stability: list[StabilityMetric],
    promoting: list[FactorConclusion],
    damaging: list[FactorConclusion],
    relationships: list[PersonNode],
    language_patterns: list[LanguageMetric],
    themes: list[ThemeTrack],
    daily_contexts: list[DailyContext] | None = None,
    environment_sensitivity: list[WeatherSensitivity] | None = None,
    space_emotions: list[SpaceEmotionLink] | None = None,
    physio_couplings: list[PhysioCoupling] | None = None,
    interaction_effects: list[InteractionEffect] | None = None,
    warning_patterns: list[WarningPattern] | None = None,
    context_completeness: dict[str, float] | None = None,
    chain_links: list[ChainLink] | None = None,
    life_story: LifeStoryBook | None = None,
    self_voice_map: SelfVoiceMap | None = None,
    reframe_candidates: list[ReframeCandidate] | None = None,
    weather_insights: list[WeatherInsight] | None = None,
) -> InsightReport:
    daily_contexts = daily_contexts or []
    environment_sensitivity = environment_sensitivity or []
    space_emotions = space_emotions or []
    physio_couplings = physio_couplings or []
    interaction_effects = interaction_effects or []
    warning_patterns = warning_patterns or []
    context_completeness = context_completeness or {}
    chain_links = chain_links or []
    reframe_candidates = reframe_candidates or []
    self_voice_map = self_voice_map or SelfVoiceMap()
    weather_insights = weather_insights or []

    sections = [
        _stability_section(stability, emotion_series),
        _factor_section("promoting", "促进因素", promoting, "promoting"),
        _factor_section("damaging", "损害因素与警示", damaging, "damaging"),
        _relationship_section(relationships, entry_count),
        _language_section(language_patterns),
        _theme_section(themes),
        _environment_section(weather_insights, environment_sensitivity, space_emotions, entry_count),
        _warning_section(warning_patterns, entry_count),
        _narrative_section(chain_links, life_story, self_voice_map, reframe_candidates),
    ]

    sections.insert(4, _interaction_section(interaction_effects, entry_count))

    limitations = _build_limitations(entry_count, emotion_series, context_completeness)
    executive_summary = _build_executive_summary(
        anchors, emotion_series, weather_insights, promoting, damaging, entry_count
    )

    completeness = {
        "entries": min(1.0, entry_count / 30),
        "emotion": min(1.0, len(emotion_series) / max(1, entry_count)),
        "weather": context_completeness.get("weather", 0),
    }

    return InsightReport(
        runId=run_id,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        entryCount=entry_count,
        dateRange=date_range,
        anchors=anchors,
        emotionSeries=emotion_series,
        stability=stability,
        promotingFactors=promoting,
        damagingFactors=damaging,
        relationships=relationships,
        languagePatterns=language_patterns,
        themes=themes,
        sections=sections,
        limitations=limitations,
        dataCompleteness=completeness,
        dailyContexts=daily_contexts,
        environmentSensitivity=environment_sensitivity,
        spaceEmotions=space_emotions,
        physioCouplings=physio_couplings,
        interactionEffects=interaction_effects,
        warningPatterns=warning_patterns,
        chainLinks=chain_links,
        lifeStory=life_story,
        selfVoiceMap=self_voice_map if self_voice_map.profiles else None,
        reframeCandidates=reframe_candidates,
        weatherInsights=weather_insights,
        executiveSummary=executive_summary,
    )


def _stability_section(stability: list[StabilityMetric], emotion_series: list) -> ReportSection:
    conclusions = []
    for m in stability:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=m.description,
                confidence=m.confidence,
                limitation="数据量有限" if m.trend == "insufficient_data" else None,
                evidence=m.evidence,
            )
        )
    if emotion_series:
        avg = sum(p.score for p in emotion_series) / len(emotion_series)
        conclusions.insert(
            0,
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"整体情绪均值为 {avg:.1f}/10（基于 {len(emotion_series)} 篇日记）",
                confidence=0.6,
                evidence=[],
            ),
        )
    return ReportSection(id="stability", title="情绪稳定性", conclusions=conclusions)


def _factor_section(
    section_id: str,
    title: str,
    factors: list[FactorConclusion],
    factor_kind: str,
) -> ReportSection:
    conclusions = []
    for f in factors:
        stmt = clean_factor_statement(f.statement)
        if f.controlled_for:
            stmt += format_controlled_for(f.controlled_for)
        implications = factor_implication(f.effect_size, factor_kind)
        conclusions.append(
            ReportConclusion(
                id=f.id,
                statement=stmt,
                confidence=f.confidence,
                evidence=f.evidence,
                implication=implications,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="在当前日记样本中暂未识别到显著因素",
                confidence=0.3,
                limitation="需要更多日记或更明显的情绪变化",
                evidence=[],
            )
        )
    return ReportSection(id=section_id, title=title, conclusions=conclusions)


def _relationship_section(relationships: list[PersonNode], entry_count: int) -> ReportSection:
    conclusions = []
    for p in relationships[:8]:
        type_label = {"positive": "净正向", "negative": "净负向", "ambivalent": "矛盾型"}.get(
            p.relationship_type.value, ""
        )
        trend = TONE_TREND_LABELS.get(p.tone_trend, "")
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=(
                    f"与「{p.name}」的关系为{type_label}，"
                    f"情绪基调 {p.emotional_tone:+.2f}，提及 {p.mention_count} 次。{trend}"
                ),
                confidence=0.55,
                evidence=p.evidence,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"在 {entry_count} 篇日记中，人物提及较少或未形成稳定关系模式",
                confidence=0.3,
                evidence=[],
            )
        )
    return ReportSection(id="relationships", title="关系健康度", conclusions=conclusions)


def _language_section(patterns: list[LanguageMetric]) -> ReportSection:
    conclusions = []
    for p in patterns:
        trend_label = LANGUAGE_TREND_LABELS.get(p.trend, p.trend)
        desc = p.description
        if trend_label and trend_label not in desc:
            desc = f"{p.name}：{desc}（趋势：{trend_label}）"
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=desc,
                confidence=p.confidence,
                evidence=p.evidence,
            )
        )
    if not conclusions:
        conclusions = [
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="语言模式数据不足",
                confidence=0.2,
                evidence=[],
            )
        ]
    return ReportSection(id="language", title="语言与思维模式变迁", conclusions=conclusions)


def _theme_section(themes: list[ThemeTrack]) -> ReportSection:
    conclusions = []
    for t in themes[:8]:
        stmt = f"主题「{t.theme}」从 {t.first_seen} 持续至 {t.last_seen}"
        if t.peak_date:
            stmt += f"，高峰出现在 {t.peak_date}"
        if t.framework_shift:
            stmt += f"，{t.framework_shift}"
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=stmt,
                confidence=0.5,
                evidence=t.evidence,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="未识别到显著主题",
                confidence=0.3,
                evidence=[],
            )
        )
    return ReportSection(id="themes", title="主题演变", conclusions=conclusions)


def _environment_section(
    weather_insights: list[WeatherInsight],
    sensitivity: list[WeatherSensitivity],
    space: list[SpaceEmotionLink],
    entry_count: int,
) -> ReportSection:
    conclusions = []
    seen_statements: set[str] = set()
    for wi in weather_insights:
        if wi.statement in seen_statements:
            continue
        seen_statements.add(wi.statement)
        conclusions.append(
            ReportConclusion(
                id=wi.id,
                statement=wi.statement,
                confidence=wi.confidence,
                evidence=wi.evidence,
            )
        )
    for sp in space:
        type_label = {"restorative": "恢复性", "stressful": "压力性", "neutral": "中性"}.get(
            sp.link_type.value, ""
        )
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"日记中的「{sp.place}」为{type_label}空间，情绪基调 {sp.emotional_tone:+.2f}",
                confidence=0.5,
                evidence=sp.evidence,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=(
                    f"在 {entry_count} 篇日记中，天气与情绪的关联尚不明显。"
                    "请在设置中保存常驻城市后重新分析，以拉取历史天气。"
                ),
                confidence=0.2,
                limitation="天气数据覆盖不足",
                evidence=[],
            )
        )
    return ReportSection(id="environment", title="天气与情绪", conclusions=conclusions)


def _warning_section(patterns: list[WarningPattern], entry_count: int) -> ReportSection:
    conclusions = [
        ReportConclusion(
            id=p.id,
            statement=p.statement,
            confidence=p.confidence,
            evidence=p.evidence,
        )
        for p in patterns
    ]
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"在 {entry_count} 篇日记中未发现稳定的个人预警组合",
                confidence=0.3,
                limitation="需要更多情绪低谷样本",
                evidence=[],
            )
        )
    return ReportSection(id="warnings", title="个人预警模式", conclusions=conclusions)


def _interaction_section(effects: list[InteractionEffect], entry_count: int) -> ReportSection:
    if effects:
        conclusions = [
            ReportConclusion(
                id=e.id,
                statement=e.statement,
                confidence=e.confidence,
                evidence=e.evidence,
            )
            for e in effects
        ]
    else:
        conclusions = [
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"在 {entry_count} 篇日记中未发现显著的因素交互效应（如雨天+周末等）",
                confidence=0.25,
                evidence=[],
            )
        ]
    return ReportSection(id="interactions", title="因素交互效应", conclusions=conclusions)


def _narrative_section(
    chain_links: list[ChainLink],
    life_story: LifeStoryBook | None,
    self_voice_map: SelfVoiceMap,
    reframe_candidates: list[ReframeCandidate],
) -> ReportSection:
    conclusions: list[ReportConclusion] = []

    if chain_links:
        by_type: dict[str, int] = {}
        for c in chain_links:
            by_type[c.type] = by_type.get(c.type, 0) + 1
        type_str = "、".join(f"{k}×{v}" for k, v in by_type.items())
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"识别到 {len(chain_links)} 条锚点关联链（{type_str}）",
                confidence=0.7,
                evidence=[e for c in chain_links[:3] for e in c.evidence[:1]],
            )
        )

    if life_story and life_story.lines:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"梳理出 {len(life_story.lines)} 条生命叙事线，可在「故事」页翻阅",
                confidence=0.65,
                evidence=[],
            )
        )

    if self_voice_map.profiles:
        voice_names = "、".join(p.label for p in self_voice_map.profiles[:4])
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"识别到多元自我声音：{voice_names}",
                confidence=0.6,
                evidence=[e for p in self_voice_map.profiles for e in p.evidence[:1]][:3],
            )
        )

    if reframe_candidates:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"发现 {len(reframe_candidates)} 条可探索的内化问题叙事，可在「重构」页发起对话",
                confidence=0.55,
                evidence=reframe_candidates[0].exception_moments[:2],
            )
        )

    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="叙事数据不足，需更多锚点或内省型日记",
                confidence=0.3,
                limitation="样本量有限",
                evidence=[],
            )
        )

    return ReportSection(id="narrative", title="叙事脉络", conclusions=conclusions)


def _build_limitations(
    entry_count: int,
    emotion_series: list,
    context_completeness: dict[str, float],
) -> list[str]:
    limits = [
        "LLM 抽取结果标注为「系统推断」，与原文明确陈述区分",
        "缺失的数据不做插补",
        "生命故事与重构对话仅提供另一种解读角度，非心理诊断或建议",
    ]
    if context_completeness.get("weather", 0) < 0.5:
        limits.append("天气数据覆盖不足：请在设置中保存常驻城市后重新分析")
    if entry_count < 30:
        limits.append(f"当前仅 {entry_count} 篇日记，统计结论置信度受限")
    if len(emotion_series) < 10:
        limits.append("情绪时间序列较短，趋势判断仅供参考")
    return limits


def _build_executive_summary(
    anchors: list[AnchorCard],
    emotion_series: list,
    weather_insights: list[WeatherInsight],
    promoting: list[FactorConclusion],
    damaging: list[FactorConclusion],
    entry_count: int,
) -> list[str]:
    bullets: list[str] = []
    if emotion_series:
        scores = [p.score for p in emotion_series]
        avg = sum(scores) / len(scores)
        best_i = max(range(len(scores)), key=lambda i: scores[i])
        worst_i = min(range(len(scores)), key=lambda i: scores[i])
        bullets.append(
            f"共 {entry_count} 篇日记，情绪均值 {avg:.1f}/10；"
            f"最高 {scores[best_i]:.1f}（{emotion_series[best_i].date}），"
            f"最低 {scores[worst_i]:.1f}（{emotion_series[worst_i].date}）。"
        )
    if weather_insights:
        bullets.append(weather_insights[0].statement)
    if anchors:
        top = sorted(anchors, key=lambda a: -a.confidence)[0]
        bullets.append(f"重要锚点：{top.date} {top.title}")
    if promoting:
        bullets.append(clean_factor_statement(promoting[0].statement))
    elif damaging:
        bullets.append(clean_factor_statement(damaging[0].statement))
    if not bullets:
        bullets.append("请继续积累日记后重新分析，以获得更稳定的洞察。")
    return bullets[:5]


def render_html(report: InsightReport) -> str:
    sections_html = ""
    for section in report.sections:
        items = ""
        for c in section.conclusions:
            ev = "".join(
                f'<li class="evidence"><span class="date">{html.escape(e.date)}</span> '
                f'{html.escape(e.text)} <em>({e.source.value})</em></li>'
                for e in c.evidence
            )
            lim = f'<p class="limitation">{html.escape(c.limitation)}</p>' if c.limitation else ""
            conf_label = _confidence_label(c.confidence)
            items += f"""
            <div class="conclusion">
              <p class="statement">{html.escape(c.statement)}</p>
              <p class="confidence">置信度: {c.confidence:.0%} ({conf_label})</p>
              {lim}
              <ul>{ev}</ul>
            </div>"""
        sections_html += f'<section><h2>{html.escape(section.title)}</h2>{items}</section>'

    limits = "".join(f"<li>{html.escape(l)}</li>" for l in report.limitations)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="color-scheme" content="light">
<title>Chronos 心理健康洞察报告</title>
<style>
  :root {{
    --bg-base: #eceae6;
    --bg-surface: #f5f4f1;
    --bg-elevated: #fafaf8;
    --text-primary: #3a3834;
    --text-muted: #7a756c;
    --accent: #6b8f7a;
    --accent-soft: rgba(107, 143, 122, 0.12);
    --border: rgba(0, 0, 0, 0.07);
    --warn-bg: rgba(160, 136, 80, 0.1);
  }}
  body {{ font-family: "Noto Sans SC", system-ui, sans-serif; background: var(--bg-base); color: var(--text-primary); max-width: 820px; margin: 2rem auto; padding: 0 1.5rem; line-height: 1.7; }}
  h1 {{ font-family: "Noto Serif SC", Georgia, serif; color: var(--text-primary); border-bottom: 2px solid var(--accent); padding-bottom: 0.5rem; font-weight: 600; }}
  h2 {{ font-family: "Noto Serif SC", Georgia, serif; color: var(--text-primary); margin-top: 2rem; font-size: 1.15rem; }}
  h3 {{ font-size: 1rem; color: var(--text-muted); }}
  .meta {{ color: var(--text-muted); font-size: 0.9rem; }}
  .conclusion {{ background: var(--bg-surface); border-left: 3px solid var(--accent); padding: 1rem 1.1rem; margin: 1rem 0; border-radius: 0 10px 10px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }}
  .statement {{ margin: 0 0 0.5rem; }}
  .confidence {{ font-size: 0.85rem; color: var(--text-muted); margin: 0; }}
  .limitation {{ font-size: 0.85rem; color: var(--text-muted); font-style: italic; }}
  .evidence {{ font-size: 0.85rem; color: var(--text-primary); margin: 0.35rem 0; }}
  .date {{ font-weight: 600; color: var(--accent); }}
  .limitations {{ background: var(--bg-elevated); padding: 1.1rem 1.25rem; border-radius: 10px; margin-top: 2rem; border: 1px solid var(--border); }}
</style>
</head>
<body>
  <h1>Chronos 心理健康洞察报告</h1>
  <p class="meta">生成时间: {html.escape(report.generated_at)} | 
  日记: {report.entry_count} 篇 | 
  {html.escape(report.date_range.get("start", ""))} — {html.escape(report.date_range.get("end", ""))}</p>
  {sections_html}
  <div class="limitations">
    <h2>局限声明</h2>
    <ul>{limits}</ul>
  </div>
</body>
</html>"""


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.7:
        return "高"
    if confidence >= 0.45:
        return "中"
    return "低"
