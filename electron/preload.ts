import { contextBridge, ipcRenderer } from 'electron';
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
} from '../src/types/analysis';

type ImportType = 'apple_health' | 'wearable_csv' | 'screen_time' | 'gpx' | 'manual_location';

contextBridge.exposeInMainWorld('chronosAPI', {
  getAppRoot: (): Promise<string> => ipcRenderer.invoke('chronos:getAppRoot'),
  getDataRoot: (): Promise<string> => ipcRenderer.invoke('chronos:getDataRoot'),

  listEntries: (): Promise<DiaryEntry[]> => ipcRenderer.invoke('chronos:listEntries'),
  getEntrySummary: (): Promise<{ count: number; firstDate: string | null; lastDate: string | null; year: number }> =>
    ipcRenderer.invoke('chronos:getEntrySummary'),

  previewImport: (sourcePath: string): Promise<ImportPreview> =>
    ipcRenderer.invoke('chronos:previewImport', sourcePath),
  importFromPath: (sourcePath: string): Promise<ImportResult> =>
    ipcRenderer.invoke('chronos:importFromPath', sourcePath),
  importFromEcho: (echoRoot: string): Promise<ImportResult> =>
    ipcRenderer.invoke('chronos:importFromEcho', echoRoot),
  syncFromEcho: (echoRoot?: string): Promise<SyncResult> =>
    ipcRenderer.invoke('chronos:syncFromEcho', echoRoot),
  pickImportPath: (): Promise<string | null> => ipcRenderer.invoke('chronos:pickImportPath'),
  pickEchoPath: (): Promise<string | null> => ipcRenderer.invoke('chronos:pickEchoPath'),

  getSettings: (): Promise<UserSettings> => ipcRenderer.invoke('chronos:getSettings'),
  saveSettings: (partial: Partial<UserSettings>): Promise<UserSettings> =>
    ipcRenderer.invoke('chronos:saveSettings', partial),
  testWeather: (): Promise<WeatherTestResult> => ipcRenderer.invoke('chronos:testWeather'),
  getContextCompleteness: (): Promise<ContextCompleteness> =>
    ipcRenderer.invoke('chronos:getContextCompleteness'),
  listContextSources: (): Promise<Record<string, number>> =>
    ipcRenderer.invoke('chronos:listContextSources'),
  pickContextFile: (type: ImportType): Promise<string | null> =>
    ipcRenderer.invoke('chronos:pickContextFile', type),
  previewCsv: (filePath: string): Promise<CsvPreview> =>
    ipcRenderer.invoke('chronos:previewCsv', filePath),
  importContext: (
    sourcePath: string,
    type: ImportType,
    columnMapping?: ColumnMapping
  ): Promise<ContextImportResult> =>
    ipcRenderer.invoke('chronos:importContext', sourcePath, type, columnMapping),
  saveManualLocation: (date: string, primaryPlace: string, placeType: string): Promise<{ ok: boolean }> =>
    ipcRenderer.invoke('chronos:saveManualLocation', date, primaryPlace, placeType),

  getStoryBook: (runId: string): Promise<LifeStoryBook | null> =>
    ipcRenderer.invoke('chronos:getStoryBook', runId),
  getSelfVoiceMap: (runId: string): Promise<SelfVoiceMap | null> =>
    ipcRenderer.invoke('chronos:getSelfVoiceMap', runId),
  listReframeCandidates: (runId: string): Promise<ReframeCandidate[]> =>
    ipcRenderer.invoke('chronos:listReframeCandidates', runId),
  saveStoryEdit: (runId: string, lineId: string, status: string, userNote?: string) =>
    ipcRenderer.invoke('chronos:saveStoryEdit', runId, lineId, status, userNote),
  reframeStart: (runId: string, candidateId: string, model: string): Promise<ReframeSession> =>
    ipcRenderer.invoke('chronos:reframeStart', runId, candidateId, model),
  reframeMessage: (
    sessionId: string,
    runId: string,
    candidateId: string,
    message: string,
    model: string
  ): Promise<ReframeSession> =>
    ipcRenderer.invoke('chronos:reframeMessage', sessionId, runId, candidateId, message, model),
  reframeFinalize: (sessionId: string, model: string): Promise<ReframeSession> =>
    ipcRenderer.invoke('chronos:reframeFinalize', sessionId, model),
  getReframeSession: (sessionId: string): Promise<ReframeSession | null> =>
    ipcRenderer.invoke('chronos:getReframeSession', sessionId),

  getEngineHealth: (): Promise<EngineHealth> => ipcRenderer.invoke('chronos:getEngineHealth'),
  listRuns: (): Promise<AnalysisRunSummary[]> => ipcRenderer.invoke('chronos:listRuns'),
  getDefaultRunId: (): Promise<string | null> => ipcRenderer.invoke('chronos:getDefaultRunId'),
  getReport: (runId: string): Promise<InsightReport | null> =>
    ipcRenderer.invoke('chronos:getReport', runId),
  startAnalysis: (model: string, resumeRunId?: string | null): Promise<InsightReport> =>
    ipcRenderer.invoke('chronos:startAnalysis', model, resumeRunId ?? null),
  cancelAnalysis: (): Promise<boolean> => ipcRenderer.invoke('chronos:cancelAnalysis'),

  getFeedback: (runId: string): Promise<import('../src/types/analysis').RunFeedback> =>
    ipcRenderer.invoke('chronos:getFeedback', runId),
  setFeedback: (
    runId: string,
    targetType: 'conclusion' | 'anchor',
    targetId: string,
    rating: 'up' | 'down' | null
  ): Promise<import('../src/types/analysis').RunFeedback> =>
    ipcRenderer.invoke('chronos:setFeedback', runId, targetType, targetId, rating),

  runBenchmark: (): Promise<import('../src/types/analysis').BenchmarkSuiteResult> =>
    ipcRenderer.invoke('chronos:runBenchmark'),
  getLastBenchmark: (): Promise<import('../src/types/analysis').BenchmarkResult | null> =>
    ipcRenderer.invoke('chronos:getLastBenchmark'),
  getLastBenchmarkSuite: (): Promise<import('../src/types/analysis').BenchmarkSuiteResult | null> =>
    ipcRenderer.invoke('chronos:getLastBenchmarkSuite'),

  getFeedbackSummary: (): Promise<import('../src/types/analysis').FeedbackSummary> =>
    ipcRenderer.invoke('chronos:getFeedbackSummary'),
  exportFeedbackJson: (): Promise<string> => ipcRenderer.invoke('chronos:exportFeedbackJson'),
  exportReportHtml: (runId: string): Promise<string | null> =>
    ipcRenderer.invoke('chronos:exportReportHtml', runId),
  exportReportJson: (runId: string): Promise<string | null> =>
    ipcRenderer.invoke('chronos:exportReportJson', runId),
  saveExport: (content: string, defaultName: string): Promise<boolean> =>
    ipcRenderer.invoke('chronos:saveExport', content, defaultName),

  getDataInventory: (): Promise<{ entries: number; analysisRuns: number; contextFiles: number }> =>
    ipcRenderer.invoke('chronos:getDataInventory'),
  deleteAllUserData: (): Promise<{
    ok: boolean;
    deleted: { entries: number; analysisRuns: number; contextFiles: number; narrativeFiles: number };
  }> => ipcRenderer.invoke('chronos:deleteAllUserData'),
  deleteDiaryEntries: (options?: {
    preserveAnonymizedAnalysis?: boolean;
  }): Promise<{
    ok: boolean;
    deleted: {
      entries: number;
      runsAnonymized: number;
      filesDeleted: number;
      filesRedacted: number;
      narrativeFiles: number;
    };
    preserveAnonymizedAnalysis: boolean;
  }> => ipcRenderer.invoke('chronos:deleteDiaryEntries', options),
  deleteAnalysisRun: (runId: string): Promise<{ ok: boolean; deleted: boolean }> =>
    ipcRenderer.invoke('chronos:deleteAnalysisRun', runId),

  onAnalysisProgress: (callback: (progress: AnalysisProgress) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, progress: AnalysisProgress) =>
      callback(progress);
    ipcRenderer.on('chronos:analysisProgress', handler);
    return () => ipcRenderer.removeListener('chronos:analysisProgress', handler);
  },
});
