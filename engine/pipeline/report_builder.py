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
    WeatherSensitivity,
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

    sections = [
        _stability_section(stability, emotion_series),
        _factor_section("promoting", "促进因素", promoting),
        _factor_section("damaging", "损害因素与警示", damaging),
        _relationship_section(relationships),
        _language_section(language_patterns),
        _theme_section(themes),
        _environment_section(environment_sensitivity, space_emotions),
        _warning_section(warning_patterns),
        _narrative_section(chain_links, life_story, self_voice_map, reframe_candidates),
    ]

    if interaction_effects:
        sections.insert(4, _interaction_section(interaction_effects))

    limitations = _build_limitations(entry_count, emotion_series, context_completeness)

    completeness = {
        "entries": min(1.0, entry_count / 30),
        "emotion": min(1.0, len(emotion_series) / max(1, entry_count)),
        "anchors": min(1.0, len(anchors) / 5),
        "factors": min(1.0, (len(promoting) + len(damaging)) / 3),
        **context_completeness,
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


def _factor_section(section_id: str, title: str, factors: list[FactorConclusion]) -> ReportSection:
    conclusions = []
    for f in factors:
        stmt = f.statement
        if f.controlled_for:
            stmt += f" [controlled: {', '.join(f.controlled_for)}]"
        conclusions.append(
            ReportConclusion(
                id=f.id,
                statement=stmt,
                confidence=f.confidence,
                evidence=f.evidence,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="暂未识别到显著因素（可能因样本量不足或因素不明显）",
                confidence=0.3,
                limitation="需要更多日记数据",
                evidence=[],
            )
        )
    return ReportSection(id=section_id, title=title, conclusions=conclusions)


def _relationship_section(relationships: list[PersonNode]) -> ReportSection:
    conclusions = []
    for p in relationships[:8]:
        type_label = {"positive": "净正向", "negative": "净负向", "ambivalent": "矛盾型"}.get(
            p.relationship_type.value, ""
        )
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=(
                    f"与「{p.name}」的关系为{type_label}，"
                    f"情绪基调 {p.emotional_tone:+.2f}，提及 {p.mention_count} 次"
                ),
                confidence=0.55,
                evidence=p.evidence,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="未识别到足够的人物关系数据",
                confidence=0.3,
                evidence=[],
            )
        )
    return ReportSection(id="relationships", title="关系健康度", conclusions=conclusions)


def _language_section(patterns: list[LanguageMetric]) -> ReportSection:
    return ReportSection(
        id="language",
        title="语言与思维模式变迁",
        conclusions=[
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=p.description,
                confidence=p.confidence,
                evidence=p.evidence,
            )
            for p in patterns
        ]
        or [
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="语言模式数据不足",
                confidence=0.2,
                evidence=[],
            )
        ],
    )


def _theme_section(themes: list[ThemeTrack]) -> ReportSection:
    conclusions = []
    for t in themes[:8]:
        stmt = f"主题「{t.theme}」从 {t.first_seen} 持续至 {t.last_seen}"
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
    sensitivity: list[WeatherSensitivity],
    space: list[SpaceEmotionLink],
) -> ReportSection:
    conclusions = []
    for s in sensitivity:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=s.description,
                confidence=s.confidence,
                evidence=s.evidence,
            )
        )
    for sp in space:
        type_label = {"restorative": "恢复性", "stressful": "压力性", "neutral": "中性"}.get(
            sp.link_type.value, ""
        )
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement=f"「{sp.place}」为{type_label}空间，情绪基调 {sp.emotional_tone:+.2f}",
                confidence=0.5,
                evidence=sp.evidence,
            )
        )
    if not conclusions:
        conclusions.append(
            ReportConclusion(
                id=str(uuid.uuid4())[:8],
                statement="环境敏感性数据不足（请配置常驻城市或导入位置数据）",
                confidence=0.2,
                limitation="缺少天气或位置数据",
                evidence=[],
            )
        )
    return ReportSection(id="environment", title="环境敏感性", conclusions=conclusions)


def _warning_section(patterns: list[WarningPattern]) -> ReportSection:
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
                statement="暂未识别到稳定的个人预警模式",
                confidence=0.3,
                limitation="需要更多多源数据与情绪低谷样本",
                evidence=[],
            )
        )
    return ReportSection(id="warnings", title="个人预警模式", conclusions=conclusions)


def _interaction_section(effects: list[InteractionEffect]) -> ReportSection:
    return ReportSection(
        id="interactions",
        title="因素交互效应",
        conclusions=[
            ReportConclusion(
                id=e.id,
                statement=e.statement,
                confidence=e.confidence,
                evidence=e.evidence,
            )
            for e in effects
        ],
    )


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
        "缺失的多源数据不做插补",
        "生命故事与重构对话仅提供另一种解读角度，非心理诊断或建议",
    ]
    if context_completeness.get("weather", 0) < 0.5:
        limits.append("天气数据覆盖不足，环境敏感性结论受限")
    if context_completeness.get("wearable", 0) < 0.3:
        limits.append("可穿戴数据不足，生理-心理耦合分析受限")
    else:
        limits.append("部分因素分析已尝试控制天气、睡眠等外部变量")
    if entry_count < 30:
        limits.append(f"当前仅 {entry_count} 篇日记，统计结论置信度受限")
    if len(emotion_series) < 10:
        limits.append("情绪时间序列较短，趋势判断仅供参考")
    return limits


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
            items += f"""
            <div class="conclusion">
              <p class="statement">{html.escape(c.statement)}</p>
              <p class="confidence">置信度: {c.confidence:.0%}</p>
              {lim}
              <ul>{ev}</ul>
            </div>"""
        sections_html += f'<section><h2>{html.escape(section.title)}</h2>{items}</section>'

    limits = "".join(f"<li>{html.escape(l)}</li>" for l in report.limitations)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Chronos 心理健康洞察报告</title>
<style>
  body {{ font-family: "Noto Serif SC", Georgia, serif; background: #f5f0e8; color: #3d3630; max-width: 800px; margin: 2rem auto; padding: 0 1.5rem; line-height: 1.7; }}
  h1 {{ color: #5c4a3a; border-bottom: 2px solid #c4a882; padding-bottom: 0.5rem; }}
  h2 {{ color: #6b5a48; margin-top: 2rem; }}
  .meta {{ color: #8a7a6a; font-size: 0.9rem; }}
  .conclusion {{ background: #faf6ee; border-left: 3px solid #c4a882; padding: 1rem; margin: 1rem 0; border-radius: 0 4px 4px 0; }}
  .confidence {{ font-size: 0.85rem; color: #8a7a6a; }}
  .evidence {{ font-size: 0.85rem; color: #5c5048; }}
  .date {{ font-weight: bold; }}
  .limitations {{ background: #fff8f0; padding: 1rem; border-radius: 4px; margin-top: 2rem; }}
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
