import fs from 'fs';
import path from 'path';

export type FeedbackRating = 'up' | 'down';

export interface FeedbackItem {
  targetType: 'conclusion' | 'anchor';
  targetId: string;
  rating: FeedbackRating;
  note?: string;
  updatedAt: string;
}

export interface RunFeedback {
  runId: string;
  updatedAt: string;
  items: Record<string, FeedbackItem>;
}

function feedbackDir(appRoot: string): string {
  return path.join(appRoot, 'data', 'feedback');
}

function feedbackPath(appRoot: string, runId: string): string {
  return path.join(feedbackDir(appRoot), `${runId}.json`);
}

function itemKey(targetType: FeedbackItem['targetType'], targetId: string): string {
  return `${targetType}:${targetId}`;
}

export function getRunFeedback(appRoot: string, runId: string): RunFeedback {
  const fp = feedbackPath(appRoot, runId);
  if (!fs.existsSync(fp)) {
    return { runId, updatedAt: new Date().toISOString(), items: {} };
  }
  try {
    return JSON.parse(fs.readFileSync(fp, 'utf-8')) as RunFeedback;
  } catch {
    return { runId, updatedAt: new Date().toISOString(), items: {} };
  }
}

export function setFeedbackItem(
  appRoot: string,
  runId: string,
  targetType: FeedbackItem['targetType'],
  targetId: string,
  rating: FeedbackRating | null,
  note?: string
): RunFeedback {
  const dir = feedbackDir(appRoot);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const current = getRunFeedback(appRoot, runId);
  const key = itemKey(targetType, targetId);
  const now = new Date().toISOString();

  if (rating === null) {
    delete current.items[key];
  } else {
    current.items[key] = {
      targetType,
      targetId,
      rating,
      note: note?.trim() || undefined,
      updatedAt: now,
    };
  }

  current.updatedAt = now;
  fs.writeFileSync(feedbackPath(appRoot, runId), JSON.stringify(current, null, 2), 'utf-8');
  return current;
}

export interface FeedbackSummary {
  total: number;
  up: number;
  down: number;
  byRun: Record<string, { up: number; down: number }>;
}

export function summarizeAllFeedback(appRoot: string): FeedbackSummary {
  const dir = feedbackDir(appRoot);
  const summary: FeedbackSummary = { total: 0, up: 0, down: 0, byRun: {} };
  if (!fs.existsSync(dir)) return summary;

  for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.json'))) {
    const runId = file.replace(/\.json$/, '');
    const fb = getRunFeedback(appRoot, runId);
    let up = 0;
    let down = 0;
    for (const item of Object.values(fb.items)) {
      summary.total += 1;
      if (item.rating === 'up') {
        summary.up += 1;
        up += 1;
      } else {
        summary.down += 1;
        down += 1;
      }
    }
    if (up + down > 0) summary.byRun[runId] = { up, down };
  }
  return summary;
}


export function exportAllFeedbackJson(appRoot: string): string {
  const dir = feedbackDir(appRoot);
  const runs: RunFeedback[] = [];
  if (fs.existsSync(dir)) {
    for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.json'))) {
      const runId = file.replace(/\.json$/, '');
      const fb = getRunFeedback(appRoot, runId);
      if (Object.keys(fb.items).length > 0) {
        runs.push(fb);
      }
    }
  }
  return JSON.stringify(
    {
      exportedAt: new Date().toISOString(),
      summary: summarizeAllFeedback(appRoot),
      runs,
    },
    null,
    2
  );
}
