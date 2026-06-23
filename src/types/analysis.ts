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
  chainLinks?: ChainLink[];
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
  dailyContexts?: DailyContext[];
  environmentSensitivity?: WeatherSensitivity[];
  spaceEmotions?: SpaceEmotionLink[];
  physioCouplings?: PhysioCoupling[];
  interactionEffects?: InteractionEffect[];
  warningPatterns?: WarningPattern[];
  chainLinks?: ChainLink[];
  lifeStory?: LifeStoryBook | null;
  selfVoiceMap?: SelfVoiceMap | null;
  reframeCandidates?: ReframeCandidate[];
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

export interface UserSettings {
  residentCity: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string;
  defaultRunId?: string | null;
}

export interface ContextCompleteness {
  weather: number;
  wearable: number;
  digital: number;
  location: number;
  rhythm: number;
}

export interface ContextImportResult {
  type: string;
  daysImported: number;
  source: string;
}

export interface ColumnMapping {
  date?: string;
  steps?: string;
  sleep?: string;
  hr?: string;
  minutes?: string;
  app?: string;
}

export interface CsvPreview {
  headers: string[];
  rows: Record<string, string>[];
}

export interface WeatherTestResult {
  ok: boolean;
  sampleTemp?: number | null;
  date?: string;
  error?: string;
}

export interface WeatherContext {
  temp?: number | null;
  humidity?: number | null;
  precipitation?: number | null;
  sunshine?: number | null;
}

export interface RhythmContext {
  weekday: number;
  weekdayLabel: string;
  month: number;
  holiday?: string | null;
  solarTerm?: string | null;
}

export interface DailyContext {
  date: string;
  weather?: WeatherContext | null;
  rhythm?: RhythmContext | null;
  missingFlags: string[];
}

export interface WeatherSensitivity {
  metric: string;
  coefficient: number;
  confidence: number;
  description: string;
  evidence: Evidence[];
}

export interface SpaceEmotionLink {
  place: string;
  emotionalTone: number;
  linkType: 'restorative' | 'stressful' | 'neutral';
  evidence: Evidence[];
}

export interface PhysioCoupling {
  metric: string;
  lagDays: number;
  correlation: number;
  leadsEmotion: boolean;
  description: string;
  evidence: Evidence[];
}

export interface InteractionEffect {
  id: string;
  factors: string[];
  effectType: 'risk' | 'protective';
  combinedEffect: number;
  exceedsAdditive: boolean;
  statement: string;
  confidence: number;
  evidence: Evidence[];
}

export interface WarningPattern {
  id: string;
  signals: string[];
  leadDays: number;
  confidence: number;
  statement: string;
  evidence: Evidence[];
}

export type ChainLinkType = 'causal' | 'theme' | 'person' | 'contrast' | 'evolution';

export interface ChainLink {
  id: string;
  type: ChainLinkType;
  anchorIds: string[];
  description: string;
  confidence: number;
  evidence: Evidence[];
}

export interface StoryNode {
  anchorId: string;
  date: string;
  title: string;
  emotionScore?: number | null;
  summary: string;
}

export type NarrativeLineStatus = 'auto' | 'accepted' | 'rejected' | 'edited';

export interface NarrativeLine {
  id: string;
  title: string;
  themeOrRelation: string;
  nodes: StoryNode[];
  emotionArc: number[];
  toneShift?: string | null;
  status: NarrativeLineStatus;
  userNote?: string | null;
}

export interface LifeStoryBook {
  runId: string;
  lines: NarrativeLine[];
  generatedAt: string;
}

export type SelfVoiceType = 'critic' | 'comforter' | 'dreamer' | 'observer' | 'other';

export interface SelfVoiceProfile {
  voiceType: SelfVoiceType;
  label: string;
  description: string;
  mentionCount: number;
  dates: string[];
  sampleQuotes: string[];
  evidence: Evidence[];
}

export interface VoiceTimelinePoint {
  date: string;
  proportions: Record<string, number>;
}

export interface VoiceTransition {
  fromVoice: string;
  toVoice: string;
  count: number;
  description: string;
}

export interface StarLayoutPoint {
  voiceType: string;
  x: number;
  y: number;
}

export interface SelfVoiceMap {
  profiles: SelfVoiceProfile[];
  timeline: VoiceTimelinePoint[];
  transitions: VoiceTransition[];
  starLayout: StarLayoutPoint[];
}

export interface ReframeCandidate {
  id: string;
  problemStatement: string;
  internalizedPattern: string;
  frequency: number;
  exceptionMoments: Evidence[];
  relatedAnchorIds: string[];
}

export interface ReframeMessage {
  role: 'user' | 'guide';
  text: string;
  timestamp: string;
}

export interface ReframeSession {
  id: string;
  runId: string;
  candidateId: string;
  messages: ReframeMessage[];
  originalNarrative: string;
  alternativeStory?: string | null;
}

export interface StoryEdit {
  status: NarrativeLineStatus;
  userNote?: string;
}
