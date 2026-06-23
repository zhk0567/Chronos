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


class ChainLink(BaseModel):
    id: str
    type: Literal["causal", "theme", "person", "contrast", "evolution"]
    anchor_ids: list[str] = Field(alias="anchorIds")
    description: str
    confidence: float
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


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
    chain_links: list[ChainLink] = Field(default_factory=list, alias="chainLinks")

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
    daily_contexts: list[DailyContext] = Field(default_factory=list, alias="dailyContexts")
    environment_sensitivity: list[WeatherSensitivity] = Field(
        default_factory=list, alias="environmentSensitivity"
    )
    space_emotions: list[SpaceEmotionLink] = Field(default_factory=list, alias="spaceEmotions")
    physio_couplings: list[PhysioCoupling] = Field(default_factory=list, alias="physioCouplings")
    interaction_effects: list[InteractionEffect] = Field(
        default_factory=list, alias="interactionEffects"
    )
    warning_patterns: list[WarningPattern] = Field(default_factory=list, alias="warningPatterns")
    chain_links: list[ChainLink] = Field(default_factory=list, alias="chainLinks")
    life_story: Optional["LifeStoryBook"] = Field(None, alias="lifeStory")
    self_voice_map: Optional["SelfVoiceMap"] = Field(None, alias="selfVoiceMap")
    reframe_candidates: list["ReframeCandidate"] = Field(
        default_factory=list, alias="reframeCandidates"
    )

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


# --- Phase 2: context & settings ---


class UserSettings(BaseModel):
    resident_city: str = Field(default="", alias="residentCity")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: str = "Asia/Shanghai"

    model_config = {"populate_by_name": True}


class WeatherContext(BaseModel):
    temp: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    sunshine: Optional[float] = None
    aqi: Optional[float] = None

    model_config = {"populate_by_name": True}


class RhythmContext(BaseModel):
    weekday: int
    weekday_label: str = Field(alias="weekdayLabel")
    month: int
    holiday: Optional[str] = None
    solar_term: Optional[str] = Field(None, alias="solarTerm")

    model_config = {"populate_by_name": True}


class WearableContext(BaseModel):
    steps: Optional[float] = None
    sleep_hours: Optional[float] = Field(None, alias="sleepHours")
    resting_hr: Optional[float] = Field(None, alias="restingHr")

    model_config = {"populate_by_name": True}


class DigitalContext(BaseModel):
    screen_time_min: Optional[float] = Field(None, alias="screenTimeMin")
    top_apps: list[str] = Field(default_factory=list, alias="topApps")

    model_config = {"populate_by_name": True}


class LocationContext(BaseModel):
    primary_place: Optional[str] = Field(None, alias="primaryPlace")
    place_type: Optional[str] = Field(None, alias="placeType")

    model_config = {"populate_by_name": True}


class DailyContext(BaseModel):
    date: str
    weather: Optional[WeatherContext] = None
    rhythm: Optional[RhythmContext] = None
    wearable: Optional[WearableContext] = None
    digital: Optional[DigitalContext] = None
    location: Optional[LocationContext] = None
    missing_flags: list[str] = Field(default_factory=list, alias="missingFlags")

    model_config = {"populate_by_name": True}


class WeatherSensitivity(BaseModel):
    metric: str
    coefficient: float
    confidence: float
    description: str
    evidence: list[Evidence] = Field(default_factory=list)


class SpaceEmotionLink(BaseModel):
    place: str
    emotional_tone: float = Field(alias="emotionalTone")
    link_type: Literal["restorative", "stressful", "neutral"] = Field(alias="linkType")
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PhysioCoupling(BaseModel):
    metric: str
    lag_days: int = Field(alias="lagDays")
    correlation: float
    leads_emotion: bool = Field(alias="leadsEmotion")
    description: str
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class InteractionEffect(BaseModel):
    id: str
    factors: list[str]
    effect_type: Literal["risk", "protective"] = Field(alias="effectType")
    combined_effect: float = Field(alias="combinedEffect")
    exceeds_additive: bool = Field(alias="exceedsAdditive")
    statement: str
    confidence: float
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class WarningPattern(BaseModel):
    id: str
    signals: list[str]
    lead_days: int = Field(alias="leadDays")
    confidence: float
    statement: str
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# --- Phase 3: narrative ---


class StoryNode(BaseModel):
    anchor_id: str = Field(alias="anchorId")
    date: str
    title: str
    emotion_score: Optional[float] = Field(None, alias="emotionScore")
    summary: str

    model_config = {"populate_by_name": True}


class NarrativeLine(BaseModel):
    id: str
    title: str
    theme_or_relation: str = Field(alias="themeOrRelation")
    nodes: list[StoryNode] = Field(default_factory=list)
    emotion_arc: list[float] = Field(default_factory=list, alias="emotionArc")
    tone_shift: Optional[str] = Field(None, alias="toneShift")
    status: Literal["auto", "accepted", "rejected", "edited"] = "auto"
    user_note: Optional[str] = Field(None, alias="userNote")

    model_config = {"populate_by_name": True}


class LifeStoryBook(BaseModel):
    run_id: str = Field(alias="runId")
    lines: list[NarrativeLine] = Field(default_factory=list)
    generated_at: str = Field(alias="generatedAt")

    model_config = {"populate_by_name": True}


class SelfVoiceProfile(BaseModel):
    voice_type: Literal["critic", "comforter", "dreamer", "observer", "other"] = Field(
        alias="voiceType"
    )
    label: str
    description: str
    mention_count: int = Field(alias="mentionCount")
    dates: list[str] = Field(default_factory=list)
    sample_quotes: list[str] = Field(default_factory=list, alias="sampleQuotes")
    evidence: list[Evidence] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class VoiceTimelinePoint(BaseModel):
    date: str
    proportions: dict[str, float]

    model_config = {"populate_by_name": True}


class VoiceTransition(BaseModel):
    from_voice: str = Field(alias="fromVoice")
    to_voice: str = Field(alias="toVoice")
    count: int
    description: str

    model_config = {"populate_by_name": True}


class StarLayoutPoint(BaseModel):
    voice_type: str = Field(alias="voiceType")
    x: float
    y: float

    model_config = {"populate_by_name": True}


class SelfVoiceMap(BaseModel):
    profiles: list[SelfVoiceProfile] = Field(default_factory=list)
    timeline: list[VoiceTimelinePoint] = Field(default_factory=list)
    transitions: list[VoiceTransition] = Field(default_factory=list)
    star_layout: list[StarLayoutPoint] = Field(default_factory=list, alias="starLayout")

    model_config = {"populate_by_name": True}


class ReframeCandidate(BaseModel):
    id: str
    problem_statement: str = Field(alias="problemStatement")
    internalized_pattern: str = Field(alias="internalizedPattern")
    frequency: int
    exception_moments: list[Evidence] = Field(default_factory=list, alias="exceptionMoments")
    related_anchor_ids: list[str] = Field(default_factory=list, alias="relatedAnchorIds")

    model_config = {"populate_by_name": True}


class ReframeMessage(BaseModel):
    role: Literal["user", "guide"]
    text: str
    timestamp: str

    model_config = {"populate_by_name": True}


class ReframeSession(BaseModel):
    id: str
    run_id: str = Field(alias="runId")
    candidate_id: str = Field(alias="candidateId")
    messages: list[ReframeMessage] = Field(default_factory=list)
    original_narrative: str = Field(alias="originalNarrative")
    alternative_story: Optional[str] = Field(None, alias="alternativeStory")

    model_config = {"populate_by_name": True}


InsightReport.model_rebuild()
