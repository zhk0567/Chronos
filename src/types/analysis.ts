export interface DiaryParagraph {
  index: number;
  text: string;
  charOffset: number;
}

export interface DiaryEntry {
  date: string;
  content: string;
  createdAt?: string;
  updatedAt?: string;
  paragraphs?: DiaryParagraph[];
}

export interface ImportPreview {
  count: number;
  firstDate: string | null;
  lastDate: string | null;
  source: string;
  year?: number;
}

export interface SyncResult {
  synced: number;
  skipped: number;
  removed: number;
  echoRoot: string | null;
  year: number;
}

export interface ImportResult {
  imported: number;
  skipped: number;
  total: number;
}

export interface AnalysisRunSummary {
  runId: string;
  startedAt: string;
  completedAt?: string;
  status: 'running' | 'completed' | 'failed';
  entryCount: number;
  error?: string;
}

export type EvidenceSource = 'explicit' | 'inferred';

export interface Evidence {
  date: string;
  text: string;
  charOffset?: number;
  charLength?: number;
  source: EvidenceSource;
}

export type MorphType = 'narrative' | 'introspective' | 'sketch' | 'list' | 'mixed';

export interface MorphResult {
  date: string;
  paragraphIndex: number;
  type: MorphType;
  confidence: number;
}

export interface SourceSpan {
  date: string;
  paragraphIndex: number;
  charOffset: number;
  charLength: number;
  text: string;
}

export interface EventPackage {
  summary?: string | null;
  participants?: string[] | null;
  location?: string | null;
  activityType?: string | null;
  emotionArc?: string | null;
}

export interface ThoughtAnchor {
  coreConcern?: string | null;
  cognitivePattern?: string | null;
  selfVoice?: string | null;
  metaphor?: string | null;
}

export interface EmotionMarker {
  label?: string | null;
  intensity?: number | null;
}

export interface RhythmInfo {
  items?: string[] | null;
  rhythmType?: string | null;
}

export type InfoUnitType = 'event_package' | 'thought_anchor' | 'emotion_marker' | 'rhythm_info';

export interface InfoUnit {
  id: string;
  date: string;
  unitType: InfoUnitType;
  morphType: MorphType;
  sourceSpan: SourceSpan;
  eventPackage?: EventPackage | null;
  thoughtAnchor?: ThoughtAnchor | null;
  emotionMarker?: EmotionMarker | null;
  rhythmInfo?: RhythmInfo | null;
  contextTags?: Record<string, unknown>;
}

export type EmergenceType =
  | 'intensity'
  | 'frequency'
  | 'structure'
  | 'narrative'
  | 'contradiction'
  | 'silence';

export interface AnchorCard {
  id: string;
  date: string;
  emergenceType: EmergenceType;
  title: string;
  description: string;
  confidence: number;
  sourceSpan?: SourceSpan | null;
  relatedUnitIds: string[];
  evidence: Evidence[];
}

export interface EmotionPoint {
  date: string;
  score: number;
  valence: number;
  arousal: number;
  confidence: number;
}

export interface StabilityMetric {
  name: string;
  trend: 'improving' | 'declining' | 'stable' | 'insufficient_data';
  value?: number | null;
  confidence: number;
  window?: string | null;
  description: string;
  evidence: Evidence[];
}

export type FactorType = 'promoting' | 'damaging' | 'pseudo_promoting';

export interface FactorConclusion {
  id: string;
  name: string;
  type: FactorType;
  effectSize: number;
  window: string;
  confidence: number;
  statement: string;
  evidence: Evidence[];
  controlledFor?: string[];
}

export type RelationshipType = 'positive' | 'negative' | 'ambivalent';

export interface PersonNode {
  name: string;
  mentionCount: number;
  emotionalTone: number;
  toneTrend: 'improving' | 'declining' | 'stable' | 'insufficient_data';
  relationshipType: RelationshipType;
  evidence: Evidence[];
}

export interface LanguageMetric {
  name: string;
  trend: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  currentRatio?: number | null;
  changePercent?: number | null;
  confidence: number;
  description: string;
  evidence: Evidence[];
}

export interface ThemeTrack {
  theme: string;
  firstSeen: string;
  lastSeen: string;
  peakDate?: string | null;
  intensityCurve: { date: string; intensity: number }[];
  frameworkShift?: string | null;
  evidence: Evidence[];
}

export interface ReportSection {
  id: string;
  title: string;
  conclusions: ReportConclusion[];
}

export interface ReportConclusion {
  id: string;
  statement: string;
  confidence: number;
  limitation?: string | null;
  evidence: Evidence[];
}

export interface InsightReport {
  runId: string;
  generatedAt: string;
  entryCount: number;
  dateRange: { start: string; end: string };
  anchors: AnchorCard[];
  emotionSeries: EmotionPoint[];
  stability: StabilityMetric[];
  promotingFactors: FactorConclusion[];
  damagingFactors: FactorConclusion[];
  relationships: PersonNode[];
  languagePatterns: LanguageMetric[];
  themes: ThemeTrack[];
  sections: ReportSection[];
  limitations: string[];
  dataCompleteness: Record<string, number>;
}

export interface AnalysisProgress {
  runId: string;
  step: string;
  stepIndex: number;
  totalSteps: number;
  message: string;
  percent: number;
}

export interface EngineHealth {
  python: boolean;
  ollama: boolean;
  ollamaModel?: string;
  error?: string;
}
