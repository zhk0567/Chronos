import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import fs from 'fs';
import path from 'path';
import {
  deleteAllUserData,
  deleteAnalysisRun,
  deleteDiaryEntries,
  getDataInventory,
} from './dataStore';
import { exportAllFeedbackJson, getRunFeedback, setFeedbackItem, summarizeAllFeedback } from './feedbackStore';
import {
  getDataRoot,
  getEntrySummary,
  importFromEcho,
  importFromSource,
  listEntries,
  previewImport,
  syncFromEcho,
  syncEchoMeta,
} from './diaryStore';
import { PythonManager } from './pythonManager';
import { AnalysisBridge } from './analysisBridge';
import {
  getStoryBook,
  getSelfVoiceMap,
  listReframeCandidates,
  saveStoryEdit,
  getReframeSession,
} from './narrativeStore';
import { getSettings, saveSettings, getContextCompleteness, type UserSettings } from './settingsStore';
import {
  runContextImport,
  listContextSources,
  testWeatherConnection,
  readCsvHeaders,
  previewCsvRows,
  saveManualLocation,
  type ImportType,
  type ColumnMapping,
} from './contextStore';

let mainWindow: BrowserWindow | null = null;
let appRoot = '';
let pythonManager: PythonManager | null = null;
let analysisBridge: AnalysisBridge | null = null;

function getAppRoot(): string {
  if (process.env.CHRONOS_APP_ROOT) return process.env.CHRONOS_APP_ROOT;

  const candidates = [
    process.env.PORTABLE_EXECUTABLE_DIR,
    process.cwd(),
    app.isPackaged ? path.dirname(app.getPath('exe')) : null,
  ].filter((d): d is string => typeof d === 'string' && d.length > 0);

  for (const dir of candidates) {
    const dataDir = path.join(dir, 'data');
    if (fs.existsSync(dataDir) || fs.existsSync(path.join(dir, 'engine'))) return dir;
  }

  return app.isPackaged ? path.dirname(app.getPath('exe')) : process.cwd();
}

function ensureDataDirs(root: string) {
  for (const sub of ['entries', 'analysis', 'reports', 'imports', 'context/weather', 'context/wearable', 'context/digital', 'context/location', 'story/edits', 'reframe/sessions', 'feedback', 'benchmark']) {
    const dir = path.join(root, 'data', sub);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    show: false,
    backgroundColor: '#eceae6',
    title: 'Chronos',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.once('ready-to-show', () => mainWindow?.show());

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

function registerIpc() {
  ipcMain.handle('chronos:getAppRoot', () => appRoot);
  ipcMain.handle('chronos:getDataRoot', () => getDataRoot(appRoot));

  ipcMain.handle('chronos:getDataInventory', () => getDataInventory(appRoot));

  ipcMain.handle('chronos:deleteAllUserData', () => deleteAllUserData(appRoot));

  ipcMain.handle(
    'chronos:deleteDiaryEntries',
    (_e, options?: { preserveAnonymizedAnalysis?: boolean }) =>
      deleteDiaryEntries(appRoot, options ?? {})
  );

  ipcMain.handle('chronos:deleteAnalysisRun', (_e, runId: string) =>
    deleteAnalysisRun(appRoot, runId)
  );

  ipcMain.handle('chronos:listEntries', () => listEntries(appRoot));
  ipcMain.handle('chronos:getEntrySummary', () => getEntrySummary(appRoot));

  ipcMain.handle('chronos:previewImport', (_e, sourcePath: string) => previewImport(sourcePath));

  ipcMain.handle('chronos:importFromPath', async (_e, sourcePath: string) => {
    return importFromSource(appRoot, sourcePath);
  });

  ipcMain.handle('chronos:importFromEcho', async (_e, echoRoot: string) => {
    return importFromEcho(appRoot, echoRoot);
  });

  ipcMain.handle('chronos:pickImportPath', async () => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile', 'openDirectory'],
      filters: [
        { name: '日记', extensions: ['json', 'txt'] },
        { name: '所有文件', extensions: ['*'] },
      ],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle('chronos:pickEchoPath', async () => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openDirectory'],
      title: '选择 Echo 项目目录',
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle('chronos:getEngineHealth', async () => {
    return analysisBridge ? pythonManager!.getHealth() : { python: false, ollama: false };
  });

  ipcMain.handle('chronos:listRuns', () => analysisBridge!.listRuns());
  ipcMain.handle('chronos:getDefaultRunId', () => analysisBridge!.getDefaultRunId());

  ipcMain.handle('chronos:getReport', (_e, runId: string) => analysisBridge!.getReport(runId));

  ipcMain.handle('chronos:exportReportHtml', (_e, runId: string) =>
    analysisBridge!.exportReportHtml(runId)
  );

  ipcMain.handle('chronos:exportReportJson', (_e, runId: string) =>
    analysisBridge!.exportReportJson(runId)
  );

  ipcMain.handle('chronos:saveExport', async (_e, content: string, defaultName: string) => {
    const result = await dialog.showSaveDialog(mainWindow!, {
      defaultPath: defaultName,
      filters: [{ name: 'Export', extensions: [defaultName.endsWith('.html') ? 'html' : 'json'] }],
    });
    if (result.canceled || !result.filePath) return false;
    fs.writeFileSync(result.filePath, content, 'utf-8');
    return true;
  });

  ipcMain.handle('chronos:syncFromEcho', async (_e, echoRoot?: string) => {
    return syncFromEcho(appRoot, echoRoot);
  });

  ipcMain.handle('chronos:getSettings', () => getSettings(appRoot));
  ipcMain.handle('chronos:saveSettings', (_e, partial: Partial<UserSettings>) =>
    saveSettings(appRoot, partial)
  );
  ipcMain.handle('chronos:getContextCompleteness', () => {
    const entries = listEntries(appRoot);
    return getContextCompleteness(
      appRoot,
      entries.map((e) => e.date)
    );
  });
  ipcMain.handle('chronos:listContextSources', () => listContextSources(appRoot));

  ipcMain.handle('chronos:testWeather', async () => {
    const settings = getSettings(appRoot);
    if (settings.latitude == null || settings.longitude == null) {
      return { ok: false, error: '请先保存常驻城市以获取坐标' };
    }
    return testWeatherConnection(appRoot, settings.latitude, settings.longitude);
  });

  ipcMain.handle('chronos:previewCsv', (_e, filePath: string) => ({
    headers: readCsvHeaders(filePath),
    rows: previewCsvRows(filePath, 3),
  }));

  ipcMain.handle(
    'chronos:importContext',
    async (_e, sourcePath: string, type: ImportType, columnMapping?: ColumnMapping) => {
      return runContextImport(appRoot, sourcePath, type, columnMapping);
    }
  );

  ipcMain.handle(
    'chronos:saveManualLocation',
    (_e, date: string, primaryPlace: string, placeType: string) => {
      saveManualLocation(appRoot, date, primaryPlace, placeType);
      return { ok: true };
    }
  );

  ipcMain.handle('chronos:pickContextFile', async (_e, type: ImportType) => {
    const filters: Record<ImportType, Electron.FileFilter[]> = {
      apple_health: [{ name: 'Apple Health', extensions: ['xml'] }],
      wearable_csv: [{ name: 'CSV', extensions: ['csv'] }],
      screen_time: [{ name: 'CSV', extensions: ['csv'] }],
      gpx: [{ name: 'GPX', extensions: ['gpx'] }],
      manual_location: [{ name: 'Location JSON', extensions: ['json'] }],
    };
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile'],
      filters: filters[type] ?? [{ name: 'All', extensions: ['*'] }],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle('chronos:startAnalysis', async (event, model: string, resumeRunId?: string | null) => {
    const entries = listEntries(appRoot);
    if (entries.length === 0) {
      throw new Error(`没有 ${new Date().getFullYear()} 年的日记可分析，请先导入或同步`);
    }

    const webContents = event.sender;
    return analysisBridge!.startAnalysis(
      entries,
      model,
      (progress) => {
        webContents.send('chronos:analysisProgress', progress);
      },
      resumeRunId ?? undefined
    );
  });

  ipcMain.handle('chronos:cancelAnalysis', () => analysisBridge!.cancelAnalysis());

  ipcMain.handle('chronos:getFeedback', (_e, runId: string) => getRunFeedback(appRoot, runId));
  ipcMain.handle(
    'chronos:setFeedback',
    (_e, runId: string, targetType: 'conclusion' | 'anchor', targetId: string, rating: 'up' | 'down' | null) =>
      setFeedbackItem(appRoot, runId, targetType, targetId, rating)
  );

  ipcMain.handle('chronos:runBenchmark', () => analysisBridge!.runBenchmark());
  ipcMain.handle('chronos:getLastBenchmark', () => analysisBridge!.getLastBenchmark());
  ipcMain.handle('chronos:getLastBenchmarkSuite', () => analysisBridge!.getLastBenchmarkSuite());
  ipcMain.handle('chronos:getFeedbackSummary', () => summarizeAllFeedback(appRoot));
  ipcMain.handle('chronos:exportFeedbackJson', () => exportAllFeedbackJson(appRoot));

  ipcMain.handle('chronos:getStoryBook', (_e, runId: string) => getStoryBook(appRoot, runId));
  ipcMain.handle('chronos:getSelfVoiceMap', (_e, runId: string) => getSelfVoiceMap(appRoot, runId));
  ipcMain.handle('chronos:listReframeCandidates', (_e, runId: string) =>
    listReframeCandidates(appRoot, runId)
  );
  ipcMain.handle(
    'chronos:saveStoryEdit',
    (_e, runId: string, lineId: string, status: string, userNote?: string) => {
      saveStoryEdit(appRoot, runId, lineId, status as 'auto' | 'accepted' | 'rejected' | 'edited', userNote);
      return { ok: true };
    }
  );
  ipcMain.handle('chronos:reframeStart', (_e, runId: string, candidateId: string, model: string) =>
    analysisBridge!.reframeStart(runId, candidateId, model)
  );
  ipcMain.handle(
    'chronos:reframeMessage',
    (_e, sessionId: string, runId: string, candidateId: string, message: string, model: string) =>
      analysisBridge!.reframeMessage(sessionId, runId, candidateId, message, model)
  );
  ipcMain.handle('chronos:reframeFinalize', (_e, sessionId: string, model: string) =>
    analysisBridge!.reframeFinalize(sessionId, model)
  );
  ipcMain.handle('chronos:getReframeSession', (_e, sessionId: string) =>
    getReframeSession(appRoot, sessionId)
  );
}

app.whenReady().then(async () => {
  appRoot = getAppRoot();
  ensureDataDirs(appRoot);

  // 启动时从同级 Echo 同步今年日记到本地 data/entries
  const sync = syncFromEcho(appRoot);
  const meta = syncEchoMeta(appRoot);
  if (sync.synced > 0 || sync.removed > 0) {
    console.log(
      `[chronos] sync ${sync.year}: ${sync.synced} entries synced, ${sync.removed} removed`
    );
  }
  if (meta.length > 0) {
    console.log(`[chronos] meta synced: ${meta.join(', ')}`);
  }

  pythonManager = new PythonManager({ appRoot, isPackaged: app.isPackaged });
  analysisBridge = new AnalysisBridge(pythonManager, appRoot);

  registerIpc();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', async () => {
  await pythonManager?.stop();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', async () => {
  await pythonManager?.stop();
});
