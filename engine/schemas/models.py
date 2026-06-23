from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceSource(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class Evidence(BaseModel):
    date: str
    text: str
    char_offset: Optional[int] = Field(None, alias="charOffset")
    char_length: Optional[int] = Field(None, alias="charLength")
    source: EvidenceSource = EvidenceSource.INFERRED

    model_config = {"populate_by_name": True}


class DiaryParagraph(BaseModel):
    index: int
    text: str
    char_offset: int = Field(alias="charOffset")

    model_config = {"populate_by_name": True}


class DiaryEntry(BaseModel):
    date: str
    content: str
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")
    paragraphs: list[DiaryParagraph] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class MorphType(str, Enum):
    NARRATIVE = "narrative"
    INTROSPECTIVE = "introspective"
    SKETCH = "sketch"
    LIST = "list"
    MIXED = "mixed"


class MorphResult(BaseModel):
    date: str
    paragraph_index: int = Field(alias="paragraphIndex")
    type: MorphType
    confidence: float = 0.8

    model_config = {"populate_by_name": True}


class SourceSpan(BaseModel):
    date: str
    paragraph_index: int = Field(alias="paragraphIndex")
    char_offset: int = Field(alias="charOffset")
    char_length: int = Field(alias="charLength")
    text: str

    model_config = {"populate_by_name": True}


class EventPackage(BaseModel):
    summary: Optional[str] = None
    participants: Optional[list[str]] = None
    location: Optional[str] = None
    activity_type: Optional[str] = Field(None, alias="activityType")
    emotion_arc: Optional[str] = Field(None, alias="emotionArc")

    model_config = {"populate_by_name": True}


class ThoughtAnchor(BaseModel):
    core_concern: Optional[str] = Field(None, alias="coreConcern")
    cognitive_pattern: Optional[str] = Field(None, alias="cognitivePattern")
    self_voice: Optional[str] = Field(None, alias="selfVoice")
    metaphor: Optional[str] = None

    model_config = {"populate_by_name": True}


class EmotionMarker(BaseModel):
    label: Optional[str] = None
    intensity: Optional[float] = None


class RhythmInfo(BaseModel):
    items: Optional[list[str]] = None
    rhythm_type: Optional[str] = Field(None, alias="rhythmType")

    model_config = {"populate_by_name": True}


class InfoUnitType(str, Enum):
    EVENT_PACKAGE = "event_package"
    THOUGHT_ANCHOR = "thought_anchor"
    EMOTION_MARKER = "emotion_marker"
    RHYTHM_INFO = "rhythm_info"


class InfoUnit(BaseModel):
    id: str
    date: str
    unit_type: InfoUnitType = Field(alias="unitType")
    morph_type: MorphType = Field(alias="morphType")
    source_span: SourceSpan = Field(alias="sourceSpan")
    event_package: Optional[EventPackage] = Field(None, alias="eventPackage")
    thought_anchor: Optional[ThoughtAnchor] = Field(None, alias="thoughtAnchor")
    emotion_marker: Optional[EmotionMarker] = Field(None, alias="emotionMarker")
    rhythm_info: Optional[RhythmInfo] = Field(None, alias="rhythmInfo")
    context_tags: dict[str, Any] = Field(default_factory=dict, alias="contextTags")

    model_config = {"populate_by_name": True}


class EmergenceType(str, Enum):
    INTENSITY = "intensity"
    FREQUENCY = "frequency"
    STRUCTURE = "structure"
    NARRATIVE = "narrative"
    CONTRADICTION = "contradiction"
    SILENCE = "silence"


class AnchorCard(BaseModel):
    id: str
    date: str
    emergence_type: EmergenceType = Field(alias="emergenceType")
    title: str
    description: str
    confidence: float
    source_span: Optional[SourceSpan] = Field(None, alias="sourceSpan")
    related_unit_ids: list[str] = Field(default_factory=list, alias="relatedUnitIds")
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class EmotionPoint(BaseModel):
    date: str
    score: float
    valence: float
    arousal: float
    confidence: float


class StabilityMetric(BaseModel):
    name: str
    trend: Literal["improving", "declining", "stable", "insufficient_data"]
    value: Optional[float] = None
    confidence: float
    window: Optional[str] = None
    description: str
    evidence: list[Evidence] = Field(default_factory=list)


class FactorType(str, Enum):
    PROMOTING = "promoting"
    DAMAGING = "damaging"
    PSEUDO_PROMOTING = "pseudo_promoting"


class FactorConclusion(BaseModel):
    id: str
    name: str
    type: FactorType
    effect_size: float = Field(alias="effectSize")
    window: str
    confidence: float
    statement: str
    evidence: list[Evidence] = Field(default_factory=list)
    controlled_for: list[str] = Field(default_factory=list, alias="controlledFor")

    model_config = {"populate_by_name": True}


class RelationshipType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    AMBIVALENT = "ambivalent"


class PersonNode(BaseModel):
    name: str
    mention_count: int = Field(alias="mentionCount")
    emotional_tone: float = Field(alias="emotionalTone")
    tone_trend: Literal["improving", "declining", "stable", "insufficient_data"] = Field(
        alias="toneTrend"
    )
    relationship_type: RelationshipType = Field(alias="relationshipType")
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class LanguageMetric(BaseModel):
    name: str
    trend: Literal["increasing", "decreasing", "stable", "insufficient_data"]
    current_ratio: Optional[float] = Field(None, alias="currentRatio")
    change_percent: Optional[float] = Field(None, alias="changePercent")
    confidence: float
    description: str
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ThemeIntensityPoint(BaseModel):
    date: str
    intensity: float


class ThemeTrack(BaseModel):
    theme: str
    first_seen: str = Field(alias="firstSeen")
    last_seen: str = Field(alias="lastSeen")
    peak_date: Optional[str] = Field(None, alias="peakDate")
    intensity_curve: list[ThemeIntensityPoint] = Field(default_factory=list, alias="intensityCurve")
    framework_shift: Optional[str] = Field(None, alias="frameworkShift")
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ReportConclusion(BaseModel):
    id: str
    statement: str
    confidence: float
    limitation: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)


class ReportSection(BaseModel):
    id: str
    title: str
    conclusions: list[ReportConclusion] = Field(default_factory=list)


class InsightReport(BaseModel):
    run_id: str = Field(alias="runId")
    generated_at: str = Field(alias="generatedAt")
    entry_count: int = Field(alias="entryCount")
    date_range: dict[str, str] = Field(alias="dateRange")
    anchors: list[AnchorCard] = Field(default_factory=list)
    emotion_series: list[EmotionPoint] = Field(default_factory=list, alias="emotionSeries")
    stability: list[StabilityMetric] = Field(default_factory=list)
    promoting_factors: list[FactorConclusion] = Field(default_factory=list, alias="promotingFactors")
    damaging_factors: list[FactorConclusion] = Field(default_factory=list, alias="damagingFactors")
    relationships: list[PersonNode] = Field(default_factory=list)
    language_patterns: list[LanguageMetric] = Field(default_factory=list, alias="languagePatterns")
    themes: list[ThemeTrack] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    data_completeness: dict[str, float] = Field(default_factory=dict, alias="dataCompleteness")

    model_config = {"populate_by_name": True}


class AnalysisRequest(BaseModel):
    run_id: str = Field(alias="runId")
    entries: list[DiaryEntry]
    model: str = "minimax-m3:cloud"

    model_config = {"populate_by_name": True}


class AnalysisProgress(BaseModel):
    run_id: str = Field(alias="runId")
    step: str
    step_index: int = Field(alias="stepIndex")
    total_steps: int = Field(alias="totalSteps")
    message: str
    percent: float

    model_config = {"populate_by_name": True}
