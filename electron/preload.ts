import { contextBridge, ipcRenderer } from 'electron';
import type {
  AnalysisProgress,
  AnalysisRunSummary,
  DiaryEntry,
  EngineHealth,
  ImportPreview,
  ImportResult,
  InsightReport,
  SyncResult,
} from '../src/types/analysis';

contextBridge.exposeInMainWorld('chronosAPI', {
  getAppRoot: (): Promise<string> => ipcRenderer.invoke('chronos:getAppRoot'),
  getDataRoot: (): Promise<string> => ipcRenderer.invoke('chronos:getDataRoot'),

  listEntries: (): Promise<DiaryEntry[]> => ipcRenderer.invoke('chronos:listEntries'),
  getEntrySummary: (): Promise<{ count: number; firstDate: string | null; lastDate: string | null }> =>
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

  getEngineHealth: (): Promise<EngineHealth> => ipcRenderer.invoke('chronos:getEngineHealth'),
  listRuns: (): Promise<AnalysisRunSummary[]> => ipcRenderer.invoke('chronos:listRuns'),
  getReport: (runId: string): Promise<InsightReport | null> =>
    ipcRenderer.invoke('chronos:getReport', runId),
  startAnalysis: (model: string): Promise<InsightReport> =>
    ipcRenderer.invoke('chronos:startAnalysis', model),
  exportReportHtml: (runId: string): Promise<string | null> =>
    ipcRenderer.invoke('chronos:exportReportHtml', runId),
  exportReportJson: (runId: string): Promise<string | null> =>
    ipcRenderer.invoke('chronos:exportReportJson', runId),
  saveExport: (content: string, defaultName: string): Promise<boolean> =>
    ipcRenderer.invoke('chronos:saveExport', content, defaultName),

  onAnalysisProgress: (callback: (progress: AnalysisProgress) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, progress: AnalysisProgress) =>
      callback(progress);
    ipcRenderer.on('chronos:analysisProgress', handler);
    return () => ipcRenderer.removeListener('chronos:analysisProgress', handler);
  },
});
