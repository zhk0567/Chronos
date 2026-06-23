import fs from 'fs';
import path from 'path';
import type {
  LifeStoryBook,
  ReframeCandidate,
  ReframeSession,
  SelfVoiceMap,
  StoryEdit,
} from '../src/types/analysis';

function runsDir(root: string): string {
  return path.join(root, 'data', 'analysis', 'runs');
}

function readJson<T>(filePath: string): T | null {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T;
  } catch {
    return null;
  }
}

export function getStoryBook(root: string, runId: string): LifeStoryBook | null {
  return readJson<LifeStoryBook>(path.join(runsDir(root), runId, 'story.json'));
}

export function getSelfVoiceMap(root: string, runId: string): SelfVoiceMap | null {
  return readJson<SelfVoiceMap>(path.join(runsDir(root), runId, 'selves.json'));
}

export function listReframeCandidates(root: string, runId: string): ReframeCandidate[] {
  return readJson<ReframeCandidate[]>(path.join(runsDir(root), runId, 'reframe_candidates.json')) ?? [];
}

function editsPath(root: string, runId: string): string {
  const dir = path.join(root, 'data', 'story', 'edits');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, `${runId}.json`);
}

export function saveStoryEdit(
  root: string,
  runId: string,
  lineId: string,
  status: StoryEdit['status'],
  userNote?: string
): void {
  const fp = editsPath(root, runId);
  const edits: Record<string, StoryEdit> = readJson(fp) ?? {};
  edits[lineId] = { status, userNote };
  fs.writeFileSync(fp, JSON.stringify(edits, null, 2), 'utf-8');

  const storyPath = path.join(runsDir(root), runId, 'story.json');
  const story = readJson<LifeStoryBook>(storyPath);
  if (story) {
    story.lines = story.lines.map((line) =>
      line.id === lineId ? { ...line, status, userNote: userNote ?? line.userNote } : line
    );
    fs.writeFileSync(storyPath, JSON.stringify(story, null, 2), 'utf-8');
  }
}

export function getReframeSession(root: string, sessionId: string): ReframeSession | null {
  return readJson<ReframeSession>(path.join(root, 'data', 'reframe', 'sessions', `${sessionId}.json`));
}
