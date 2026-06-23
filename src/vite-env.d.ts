/// <reference types="vite/client" />

import type {
  AnalysisProgress,
  AnalysisRunSummary,
  DiaryEntry,
  EngineHealth,
  ImportPreview,
  ImportResult,
  InsightReport,
  SyncResult,
} from './types/analysis';

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
  getEngineHealth(): Promise<EngineHealth>;
  listRuns(): Promise<AnalysisRunSummary[]>;
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
