import fs from 'fs';
import path from 'path';
import type { DiaryEntry, DiaryParagraph, ImportPreview, ImportResult } from '../src/types/analysis';
import { getAnalysisYear, isInAnalysisYear, yearFilePattern } from './yearFilter';

const DATE_LINE_RE = /^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s*$/;

function normalizeDate(raw: string): string {
  const parts = raw.replace(/[/.]/g, '-').split('-');
  const y = parts[0];
  const m = parts[1].padStart(2, '0');
  const d = parts[2].padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function splitParagraphs(content: string): DiaryParagraph[] {
  const blocks = content.split(/\n\s*\n/);
  const paragraphs: DiaryParagraph[] = [];
  let offset = 0;
  for (let i = 0; i < blocks.length; i++) {
    const text = blocks[i].trim();
    if (!text) {
      offset += blocks[i].length + 2;
      continue;
    }
    const idx = content.indexOf(text, offset);
    paragraphs.push({
      index: paragraphs.length,
      text,
      charOffset: idx >= 0 ? idx : offset,
    });
    offset = (idx >= 0 ? idx : offset) + text.length + 2;
  }
  if (paragraphs.length === 0 && content.trim()) {
    paragraphs.push({ index: 0, text: content.trim(), charOffset: 0 });
  }
  return paragraphs;
}

function enrichEntry(entry: DiaryEntry): DiaryEntry {
  return {
    ...entry,
    paragraphs: splitParagraphs(entry.content),
  };
}

function entriesDir(root: string): string {
  return path.join(root, 'data', 'entries');
}

function ensureDirs(root: string) {
  for (const sub of ['entries', 'analysis', 'reports']) {
    const dir = path.join(root, 'data', sub);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }
}

export function getDataRoot(appRoot: string): string {
  return path.join(appRoot, 'data');
}

export function listEntries(root: string, year = getAnalysisYear()): DiaryEntry[] {
  ensureDirs(root);
  const dir = entriesDir(root);
  if (!fs.existsSync(dir)) return [];
  const pattern = yearFilePattern(year);
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json') && !f.startsWith('_') && pattern.test(f));
  const entries: DiaryEntry[] = [];
  for (const file of files) {
    try {
      const raw = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf-8')) as DiaryEntry;
      if (raw.date && raw.content && isInAnalysisYear(raw.date, year)) {
        entries.push(enrichEntry(raw));
      }
    } catch {
      /* skip invalid */
    }
  }
  return entries.sort((a, b) => a.date.localeCompare(b.date));
}

/** 移除本地非分析年份的日记文件 */
export function pruneNonCurrentYearEntries(root: string, year = getAnalysisYear()): number {
  ensureDirs(root);
  const dir = entriesDir(root);
  if (!fs.existsSync(dir)) return 0;
  const pattern = yearFilePattern(year);
  let removed = 0;
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith('.json') || file.startsWith('_')) continue;
    if (!pattern.test(file)) {
      fs.unlinkSync(path.join(dir, file));
      removed++;
    }
  }
  return removed;
}

export function saveEntry(root: string, entry: DiaryEntry): void {
  ensureDirs(root);
  const filePath = path.join(entriesDir(root), `${entry.date}.json`);
  const now = new Date().toISOString();
  const payload = {
    date: entry.date,
    content: entry.content,
    createdAt: entry.createdAt ?? now,
    updatedAt: now,
  };
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), 'utf-8');
}

export function previewImport(sourcePath: string): ImportPreview {
  const stat = fs.statSync(sourcePath);
  let dates: string[] = [];

  if (stat.isDirectory()) {
    const files = fs.readdirSync(sourcePath).filter((f) => f.endsWith('.json'));
    for (const file of files) {
      try {
        const raw = JSON.parse(fs.readFileSync(path.join(sourcePath, file), 'utf-8')) as DiaryEntry;
        if (raw.date) dates.push(raw.date);
      } catch {
        /* skip */
      }
    }
  } else if (sourcePath.endsWith('.json')) {
    try {
      const raw = JSON.parse(fs.readFileSync(sourcePath, 'utf-8'));
      if (Array.isArray(raw)) {
        dates = raw.filter((e) => e.date).map((e) => e.date);
      } else if (raw.date) {
        dates = [raw.date];
      }
    } catch {
      /* fall through to txt */
    }
  }

  if (dates.length === 0 && stat.isFile()) {
    dates = parseTxtDates(fs.readFileSync(sourcePath, 'utf-8'));
  }

  const year = getAnalysisYear();
  dates = dates.filter((d) => isInAnalysisYear(d, year)).sort();
  return {
    count: dates.length,
    firstDate: dates[0] ?? null,
    lastDate: dates[dates.length - 1] ?? null,
    source: sourcePath,
    year,
  };
}

function parseTxtDates(content: string): string[] {
  const dates: string[] = [];
  const lines = content.split(/\r?\n/);
  let currentDate: string | null = null;
  let body = '';

  function flush() {
    if (currentDate && body.trim()) dates.push(currentDate);
    body = '';
  }

  for (const line of lines) {
    const m = line.match(DATE_LINE_RE);
    if (m) {
      flush();
      currentDate = normalizeDate(m[1]);
    } else {
      body += line + '\n';
    }
  }
  flush();
  return dates;
}

export function importFromSource(root: string, sourcePath: string): ImportResult {
  ensureDirs(root);
  const stat = fs.statSync(sourcePath);
  let imported = 0;
  let skipped = 0;

  const year = getAnalysisYear();

  const importOne = (entry: DiaryEntry) => {
    if (!isInAnalysisYear(entry.date, year)) {
      skipped++;
      return;
    }
    const dest = path.join(entriesDir(root), `${entry.date}.json`);
    if (fs.existsSync(dest)) {
      skipped++;
      return;
    }
    saveEntry(root, entry);
    imported++;
  };

  if (stat.isDirectory()) {
    const files = fs.readdirSync(sourcePath).filter((f) => f.endsWith('.json') && !f.startsWith('_'));
    for (const file of files) {
      try {
        const raw = JSON.parse(fs.readFileSync(path.join(sourcePath, file), 'utf-8')) as DiaryEntry;
        if (raw.date && raw.content) importOne(raw);
      } catch {
        skipped++;
      }
    }
  } else if (sourcePath.endsWith('.json')) {
    const raw = JSON.parse(fs.readFileSync(sourcePath, 'utf-8'));
    if (Array.isArray(raw)) {
      for (const e of raw) {
        if (e.date && e.content) importOne(e);
        else skipped++;
      }
    } else if (raw.date && raw.content) {
      importOne(raw);
    }
  } else {
    const content = fs.readFileSync(sourcePath, 'utf-8');
    const entries = parseTxtEntries(content);
    for (const e of entries) importOne(e);
  }

  return { imported, skipped, total: imported + skipped };
}

function parseTxtEntries(content: string): DiaryEntry[] {
  const lines = content.split(/\r?\n/);
  const entries: DiaryEntry[] = [];
  let currentDate: string | null = null;
  let body = '';

  function flush() {
    if (currentDate && body.trim()) {
      entries.push({ date: currentDate, content: body.trim() });
    }
    body = '';
  }

  for (const line of lines) {
    const m = line.match(DATE_LINE_RE);
    if (m) {
      flush();
      currentDate = normalizeDate(m[1]);
    } else {
      body += line + '\n';
    }
  }
  flush();
  return entries;
}

export function importFromEcho(root: string, echoRoot: string): ImportResult {
  const echoEntries = path.join(echoRoot, 'entries');
  if (!fs.existsSync(echoEntries)) {
    throw new Error(`Echo entries 目录不存在: ${echoEntries}`);
  }
  return importFromSource(root, echoEntries);
}

export interface SyncResult {
  synced: number;
  skipped: number;
  removed: number;
  echoRoot: string | null;
  year: number;
}

/** 从 Echo 同步今年日记到本地，覆盖已有条目并清除非今年数据 */
export function syncFromEcho(root: string, echoRoot?: string): SyncResult {
  const resolvedEcho = echoRoot ?? findSiblingEcho(root);
  const removed = pruneNonCurrentYearEntries(root);

  if (!resolvedEcho) {
    return { synced: 0, skipped: 0, removed, echoRoot: null, year: getAnalysisYear() };
  }

  const echoEntries = path.join(resolvedEcho, 'entries');
  if (!fs.existsSync(echoEntries)) {
    return { synced: 0, skipped: 0, removed, echoRoot: resolvedEcho, year: getAnalysisYear() };
  }

  ensureDirs(root);
  const year = getAnalysisYear();
  const pattern = yearFilePattern(year);
  let synced = 0;
  let skipped = 0;

  for (const file of fs.readdirSync(echoEntries)) {
    if (!pattern.test(file)) continue;
    const src = path.join(echoEntries, file);
    const dest = path.join(entriesDir(root), file);
    try {
      const raw = JSON.parse(fs.readFileSync(src, 'utf-8')) as DiaryEntry;
      if (!raw.date || !raw.content || !isInAnalysisYear(raw.date, year)) {
        skipped++;
        continue;
      }
      fs.copyFileSync(src, dest);
      synced++;
    } catch {
      skipped++;
    }
  }

  return { synced, skipped, removed, echoRoot: resolvedEcho, year };
}

function findSiblingEcho(appRoot: string): string | null {
  const candidate = path.join(path.dirname(appRoot), 'Echo');
  if (fs.existsSync(path.join(candidate, 'entries'))) return candidate;
  return null;
}

/** 复制 Echo 辅助数据到 data/meta/ */
export function syncEchoMeta(root: string, echoRoot?: string): string[] {
  const resolvedEcho = echoRoot ?? findSiblingEcho(root);
  if (!resolvedEcho) return [];

  const metaDir = path.join(root, 'data', 'meta');
  if (!fs.existsSync(metaDir)) fs.mkdirSync(metaDir, { recursive: true });

  const copied: string[] = [];
  for (const file of ['name-watchlist.json']) {
    const src = path.join(resolvedEcho, file);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, path.join(metaDir, file));
      copied.push(file);
    }
  }
  return copied;
}

export function getEntrySummary(root: string): {
  count: number;
  firstDate: string | null;
  lastDate: string | null;
  year: number;
} {
  const year = getAnalysisYear();
  const entries = listEntries(root, year);
  return {
    count: entries.length,
    firstDate: entries[0]?.date ?? null,
    lastDate: entries[entries.length - 1]?.date ?? null,
    year,
  };
}
