from __future__ import annotations

import html
import json
import uuid
from datetime import datetime, timezone

from schemas.models import (
    AnchorCard,
    FactorConclusion,
    InsightReport,
    LanguageMetric,
    PersonNode,
    ReportConclusion,
    ReportSection,
    StabilityMetric,
    ThemeTrack,
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
) -> InsightReport:
    sections = [
        _stability_section(stability, emotion_series),
        _factor_section("promoting", "促进因素", promoting),
        _factor_section("damaging", "损害因素与警示", damaging),
        _relationship_section(relationships),
        _language_section(language_patterns),
        _theme_section(themes),
    ]

    limitations = _build_limitations(entry_count, emotion_series)

    completeness = {
        "entries": min(1.0, entry_count / 30),
        "emotion": min(1.0, len(emotion_series) / max(1, entry_count)),
        "anchors": min(1.0, len(anchors) / 5),
        "factors": min(1.0, (len(promoting) + len(damaging)) / 3),
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
    conclusions = [
        ReportConclusion(
            id=f.id,
            statement=f.statement,
            confidence=f.confidence,
            evidence=f.evidence,
        )
        for f in factors
    ]
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


def _build_limitations(entry_count: int, emotion_series: list) -> list[str]:
    limits = [
        "所有推断均基于日记文本，未控制外部变量（天气、睡眠等）",
        "LLM 抽取结果标注为「系统推断」，与原文明确陈述区分",
    ]
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
