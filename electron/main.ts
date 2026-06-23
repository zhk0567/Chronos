import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import fs from 'fs';
import path from 'path';
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
  for (const sub of ['entries', 'analysis', 'reports']) {
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
    backgroundColor: '#f5f0e8',
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
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

function registerIpc() {
  ipcMain.handle('chronos:getAppRoot', () => appRoot);
  ipcMain.handle('chronos:getDataRoot', () => getDataRoot(appRoot));

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

  ipcMain.handle('chronos:startAnalysis', async (event, model: string) => {
    const entries = listEntries(appRoot);
    if (entries.length === 0) {
      throw new Error(`没有 ${new Date().getFullYear()} 年的日记可分析，请先导入或同步`);
    }

    const webContents = event.sender;
    return analysisBridge!.startAnalysis(entries, model, (progress) => {
      webContents.send('chronos:analysisProgress', progress);
    });
  });
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
