import fs from 'fs';
import path from 'path';

const REDACTED = '[已脱敏]';

const DELETE_FILES = new Set([
  'units.json',
  'morphs.json',
  'language.json',
  'reframe_candidates.json',
  'report.html',
]);

const REDACT_FILES = new Set([
  'anchors.json',
  'chains.json',
  'story.json',
  'report.json',
  'network.json',
  'factors.json',
  'emotion.json',
  'themes.json',
  'environment.json',
  'physio.json',
  'warnings.json',
  'interactions.json',
  'selves.json',
]);

function redactValue(key: string, value: unknown): unknown {
  if (value == null) return value;

  if (key === 'text' || key === 'content') {
    return typeof value === 'string' && value.length > 0 ? REDACTED : value;
  }

  if (key === 'sourceSpan' && typeof value === 'object' && value !== null) {
    const span = { ...(value as Record<string, unknown>) };
    if (typeof span.text === 'string' && span.text.length > 0) span.text = REDACTED;
    span.charOffset = 0;
    span.charLength = 0;
    return span;
  }

  if (key === 'evidence' && Array.isArray(value)) {
    return value.map((item) => redactNode(item));
  }

  if (Array.isArray(value)) {
    return value.map((item) => redactNode(item));
  }

  if (typeof value === 'object') {
    return redactNode(value as Record<string, unknown>);
  }

  return value;
}

function redactNode(node: unknown): unknown {
  if (node == null || typeof node !== 'object') return node;
  if (Array.isArray(node)) return node.map((item) => redactNode(item));

  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
    out[key] = redactValue(key, value);
  }
  return out;
}

/** 脱敏单个分析 run：删除含原文的文件，并抹除其余产物中的 evidence / 原文片段。 */
export function anonymizeRunArtifacts(runDir: string): { deletedFiles: number; redactedFiles: number } {
  if (!fs.existsSync(runDir)) {
    return { deletedFiles: 0, redactedFiles: 0 };
  }

  let deletedFiles = 0;
  let redactedFiles = 0;

  for (const name of fs.readdirSync(runDir)) {
    const full = path.join(runDir, name);
    if (!fs.statSync(full).isFile()) continue;

    if (DELETE_FILES.has(name)) {
      fs.unlinkSync(full);
      deletedFiles += 1;
      continue;
    }

    if (!REDACT_FILES.has(name) || !name.endsWith('.json')) continue;

    try {
      const raw = fs.readFileSync(full, 'utf-8');
      const parsed = JSON.parse(raw) as unknown;
      const redacted = redactNode(parsed);
      fs.writeFileSync(full, JSON.stringify(redacted, null, 2), 'utf-8');
      redactedFiles += 1;
    } catch {
      // 跳过无法解析的文件
    }
  }

  const metaPath = path.join(runDir, 'meta.json');
  if (fs.existsSync(metaPath)) {
    try {
      const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8')) as Record<string, unknown>;
      meta.anonymized = true;
      meta.anonymizedAt = new Date().toISOString();
      meta.entriesDeleted = true;
      fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2), 'utf-8');
    } catch {
      // ignore
    }
  }

  return { deletedFiles, redactedFiles };
}

export function anonymizeAllRunArtifacts(appRoot: string): {
  runsProcessed: number;
  deletedFiles: number;
  redactedFiles: number;
} {
  const runsDir = path.join(appRoot, 'data', 'analysis', 'runs');
  if (!fs.existsSync(runsDir)) {
    return { runsProcessed: 0, deletedFiles: 0, redactedFiles: 0 };
  }

  let runsProcessed = 0;
  let deletedFiles = 0;
  let redactedFiles = 0;

  for (const runId of fs.readdirSync(runsDir)) {
    const runDir = path.join(runsDir, runId);
    if (!fs.statSync(runDir).isDirectory()) continue;
    const result = anonymizeRunArtifacts(runDir);
    runsProcessed += 1;
    deletedFiles += result.deletedFiles;
    redactedFiles += result.redactedFiles;
  }

  return { runsProcessed, deletedFiles, redactedFiles };
}
