import fs from 'fs';
import path from 'path';

import { anonymizeAllRunArtifacts } from './anonymizeRuns';
import { getSettings, saveSettings } from './settingsStore';

export type DeleteUserDataResult = {
  ok: boolean;
  deleted: {
    entries: number;
    analysisRuns: number;
    contextFiles: number;
    narrativeFiles: number;
  };
};

export type DeleteDiaryEntriesResult = {
  ok: boolean;
  deleted: {
    entries: number;
    runsAnonymized: number;
    filesDeleted: number;
    filesRedacted: number;
    narrativeFiles: number;
  };
  preserveAnonymizedAnalysis: boolean;
};

function rmDirContents(dir: string): number {
  if (!fs.existsSync(dir)) return 0;
  let count = 0;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      count += rmDirContents(full);
      fs.rmdirSync(full);
    } else {
      fs.unlinkSync(full);
      count += 1;
    }
  }
  return count;
}

function countFilesRecursive(dir: string): number {
  if (!fs.existsSync(dir)) return 0;
  let count = 0;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) {
      count += countFilesRecursive(full);
    } else {
      count += 1;
    }
  }
  return count;
}

/** 删除本地全部用户数据（日记、分析、语境、叙事编辑），保留 settings 结构但清除 defaultRunId。 */
export function deleteAllUserData(appRoot: string): DeleteUserDataResult {
  const dataRoot = path.join(appRoot, 'data');
  const entriesDir = path.join(dataRoot, 'entries');
  const runsDir = path.join(dataRoot, 'analysis', 'runs');
  const contextDir = path.join(dataRoot, 'context');
  const storyEditsDir = path.join(dataRoot, 'story', 'edits');
  const reframeDir = path.join(dataRoot, 'reframe', 'sessions');

  const entries = rmDirContents(entriesDir);
  const runs = rmDirContents(runsDir);
  const context = rmDirContents(contextDir);
  const narrative =
    rmDirContents(storyEditsDir) + rmDirContents(reframeDir);

  const settings = getSettings(appRoot);
  if (settings.defaultRunId) {
    saveSettings(appRoot, { defaultRunId: undefined });
  }

  return {
    ok: true,
    deleted: {
      entries,
      analysisRuns: runs,
      contextFiles: context,
      narrativeFiles: narrative,
    },
  };
}

function deleteEntryFiles(entriesDir: string): number {
  if (!fs.existsSync(entriesDir)) return 0;
  let count = 0;
  for (const name of fs.readdirSync(entriesDir)) {
    if (!name.endsWith('.json')) continue;
    fs.unlinkSync(path.join(entriesDir, name));
    count += 1;
  }
  return count;
}

function clearNarrativeEdits(appRoot: string): number {
  const storyEditsDir = path.join(appRoot, 'data', 'story', 'edits');
  const reframeDir = path.join(appRoot, 'data', 'reframe', 'sessions');
  return rmDirContents(storyEditsDir) + rmDirContents(reframeDir);
}

/**
 * 删除全部日记原文。可选保留脱敏后的分析产物（聚合统计与报告结构，不含可还原原文）。
 */
export function deleteDiaryEntries(
  appRoot: string,
  options: { preserveAnonymizedAnalysis?: boolean } = {}
): DeleteDiaryEntriesResult {
  const preserve = options.preserveAnonymizedAnalysis === true;
  const entriesDir = path.join(appRoot, 'data', 'entries');
  const entries = deleteEntryFiles(entriesDir);

  let runsAnonymized = 0;
  let filesDeleted = 0;
  let filesRedacted = 0;
  let narrativeFiles = 0;

  if (preserve) {
    const anon = anonymizeAllRunArtifacts(appRoot);
    runsAnonymized = anon.runsProcessed;
    filesDeleted = anon.deletedFiles;
    filesRedacted = anon.redactedFiles;
    narrativeFiles = clearNarrativeEdits(appRoot);
  }

  return {
    ok: true,
    deleted: {
      entries,
      runsAnonymized,
      filesDeleted,
      filesRedacted,
      narrativeFiles,
    },
    preserveAnonymizedAnalysis: preserve,
  };
}

/** 删除单个分析 run 目录（用于放弃未完成的分析）。 */
export function deleteAnalysisRun(appRoot: string, runId: string): { ok: boolean; deleted: boolean } {
  const runDir = path.join(appRoot, 'data', 'analysis', 'runs', runId);
  if (!fs.existsSync(runDir)) {
    return { ok: true, deleted: false };
  }
  fs.rmSync(runDir, { recursive: true, force: true });

  const settings = getSettings(appRoot);
  if (settings.defaultRunId === runId) {
    saveSettings(appRoot, { defaultRunId: undefined });
  }

  return { ok: true, deleted: true };
}

export function getDataInventory(appRoot: string): {
  entries: number;
  analysisRuns: number;
  contextFiles: number;
} {
  const dataRoot = path.join(appRoot, 'data');
  const entriesDir = path.join(dataRoot, 'entries');
  const runsDir = path.join(dataRoot, 'analysis', 'runs');
  const contextDir = path.join(dataRoot, 'context');

  let entries = 0;
  if (fs.existsSync(entriesDir)) {
    entries = fs.readdirSync(entriesDir).filter((f) => f.endsWith('.json')).length;
  }

  let runs = 0;
  if (fs.existsSync(runsDir)) {
    runs = fs.readdirSync(runsDir).filter((f) => fs.statSync(path.join(runsDir, f)).isDirectory()).length;
  }

  return {
    entries,
    analysisRuns: runs,
    contextFiles: countFilesRecursive(contextDir),
  };
}
