import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

export type ImportType =
  | 'apple_health'
  | 'wearable_csv'
  | 'screen_time'
  | 'gpx'
  | 'manual_location';

export interface ColumnMapping {
  date?: string;
  steps?: string;
  sleep?: string;
  hr?: string;
  minutes?: string;
  app?: string;
}

export interface ImportResult {
  type: ImportType;
  daysImported: number;
  source: string;
}

export interface WeatherTestResult {
  ok: boolean;
  sampleTemp?: number | null;
  date?: string;
  error?: string;
}

function ensureImportDir(root: string): string {
  const dir = path.join(root, 'data', 'imports');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function resolvePython(root: string): string {
  const venv = path.join(root, '.venv', 'Scripts', 'python.exe');
  return fs.existsSync(venv) ? venv : 'python';
}

export function runContextImport(
  root: string,
  sourcePath: string,
  type: ImportType,
  columnMapping?: ColumnMapping
): Promise<ImportResult> {
  const importDir = ensureImportDir(root);
  const dest = path.join(importDir, path.basename(sourcePath));
  fs.copyFileSync(sourcePath, dest);
  const dataDir = path.join(root, 'data');
  const python = resolvePython(root);
  const engineDir = path.join(root, 'engine');
  const mappingArg = columnMapping ? JSON.stringify(columnMapping) : '';

  return new Promise((resolve, reject) => {
    const args = ['-m', 'context.import_cli', type, dest, dataDir];
    if (mappingArg) args.push(mappingArg);
    const proc = spawn(python, args, { cwd: engineDir, env: { ...process.env, PYTHONUTF8: '1' } });
    let stdout = '';
    proc.stdout.on('data', (d) => (stdout += d.toString()));
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Import failed (code ${code})`));
        return;
      }
      try {
        const result = JSON.parse(stdout.trim());
        resolve({ type, daysImported: result.daysImported ?? 0, source: dest });
      } catch {
        reject(new Error('Invalid import response'));
      }
    });
  });
}

export function saveManualLocation(
  root: string,
  date: string,
  primaryPlace: string,
  placeType: string
): void {
  const outDir = path.join(root, 'data', 'context', 'location');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  const data = { primaryPlace, placeType };
  fs.writeFileSync(path.join(outDir, `${date}.json`), JSON.stringify(data, null, 2), 'utf-8');
}

export function readCsvHeaders(filePath: string): string[] {
  const content = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '');
  const firstLine = content.split(/\r?\n/)[0] ?? '';
  return firstLine.split(',').map((h) => h.trim().replace(/^"|"$/g, '')).filter(Boolean);
}

export function previewCsvRows(filePath: string, limit = 3): Record<string, string>[] {
  const content = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '');
  const lines = content.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
  const rows: Record<string, string>[] = [];
  for (const line of lines.slice(1, 1 + limit)) {
    const cols = line.split(',').map((c) => c.trim().replace(/^"|"$/g, ''));
    const row: Record<string, string> = {};
    headers.forEach((h, i) => {
      row[h] = cols[i] ?? '';
    });
    rows.push(row);
  }
  return rows;
}

export function testWeatherConnection(root: string, lat: number, lng: number): Promise<WeatherTestResult> {
  const python = resolvePython(root);
  const engineDir = path.join(root, 'engine');

  return new Promise((resolve, reject) => {
    const proc = spawn(
      python,
      ['-m', 'context.weather_cli', String(lat), String(lng)],
      { cwd: engineDir, env: { ...process.env, PYTHONUTF8: '1' } }
    );
    let stdout = '';
    proc.stdout.on('data', (d) => (stdout += d.toString()));
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Weather test failed (code ${code})`));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()) as WeatherTestResult);
      } catch {
        reject(new Error('Invalid weather test response'));
      }
    });
  });
}

export function listContextSources(root: string): Record<string, number> {
  const result: Record<string, number> = {};
  for (const sub of ['weather', 'wearable', 'digital', 'location']) {
    const dir = path.join(root, 'data', 'context', sub);
    if (fs.existsSync(dir)) {
      result[sub] = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).length;
    } else {
      result[sub] = 0;
    }
  }
  return result;
}
