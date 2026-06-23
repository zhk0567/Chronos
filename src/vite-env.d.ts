/// <reference types="vite/client" />

import type {
  AnalysisProgress,
  AnalysisRunSummary,
  ColumnMapping,
  ContextCompleteness,
  ContextImportResult,
  CsvPreview,
  DiaryEntry,
  EngineHealth,
  ImportPreview,
  ImportResult,
  InsightReport,
  LifeStoryBook,
  ReframeCandidate,
  ReframeSession,
  SelfVoiceMap,
  SyncResult,
  UserSettings,
  WeatherTestResult,
} from './types/analysis';

type ImportType = 'apple_health' | 'wearable_csv' | 'screen_time' | 'gpx' | 'manual_location';

export interface ChronosAPI {
  getAppRoot(): Promise<string>;
  getDataRoot(): Promise<string>;
  listEntries(): Promise<DiaryEntry[]>;
  getEntrySummary(): Promise<{ count: number; firstDate: string | null; lastDate: string | null; year: number }>;
  previewImport(sourcePath: string): Promise<ImportPreview>;
  importFromPath(sourcePath: string): Promise<ImportResult>;
  importFromEcho(echoRoot: string): Promise<ImportResult>;
  syncFromEcho(echoRoot?: string): Promise<SyncResult>;
  pickImportPath(): Promise<string | null>;
  pickEchoPath(): Promise<string | null>;
  getSettings(): Promise<UserSettings>;
  saveSettings(partial: Partial<UserSettings>): Promise<UserSettings>;
  testWeather(): Promise<WeatherTestResult>;
  getContextCompleteness(): Promise<ContextCompleteness>;
  listContextSources(): Promise<Record<string, number>>;
  pickContextFile(type: ImportType): Promise<string | null>;
  previewCsv(filePath: string): Promise<CsvPreview>;
  importContext(sourcePath: string, type: ImportType, columnMapping?: ColumnMapping): Promise<ContextImportResult>;
  saveManualLocation(date: string, primaryPlace: string, placeType: string): Promise<{ ok: boolean }>;
  getStoryBook(runId: string): Promise<LifeStoryBook | null>;
  getSelfVoiceMap(runId: string): Promise<SelfVoiceMap | null>;
  listReframeCandidates(runId: string): Promise<ReframeCandidate[]>;
  saveStoryEdit(runId: string, lineId: string, status: string, userNote?: string): Promise<{ ok: boolean }>;
  reframeStart(runId: string, candidateId: string, model: string): Promise<ReframeSession>;
  reframeMessage(sessionId: string, runId: string, candidateId: string, message: string, model: string): Promise<ReframeSession>;
  reframeFinalize(sessionId: string, model: string): Promise<ReframeSession>;
  getReframeSession(sessionId: string): Promise<ReframeSession | null>;
  getEngineHealth(): Promise<EngineHealth>;
  listRuns(): Promise<AnalysisRunSummary[]>;
  getDefaultRunId(): Promise<string | null>;
  getReport(runId: string): Promise<InsightReport | null>;
  startAnalysis(model: string): Promise<InsightReport>;
  exportReportHtml(runId: string): Promise<string | null>;
  exportReportJson(runId: string): Promise<string | null>;
  saveExport(content: string, defaultName: string): Promise<boolean>;
  onAnalysisProgress(callback: (progress: AnalysisProgress) => void): () => void;
}

declare global {
  interface Window {
    chronosAPI: ChronosAPI;
  }
}

export {};
