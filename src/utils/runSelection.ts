import type { AnalysisRunSummary } from '../types/analysis';

export async function resolveRunId(
  navRunId: string | null,
  currentRunId: string | null,
  completedOnly = false
): Promise<{ runId: string | null; runs: AnalysisRunSummary[] }> {
  const list = await window.chronosAPI.listRuns();
  const runs = completedOnly ? list.filter((r) => r.status === 'completed') : list;

  if (currentRunId) {
    return { runId: currentRunId, runs };
  }
  if (navRunId && runs.some((r) => r.runId === navRunId)) {
    return { runId: navRunId, runs };
  }

  const defaultId = await window.chronosAPI.getDefaultRunId();
  if (defaultId && runs.some((r) => r.runId === defaultId)) {
    return { runId: defaultId, runs };
  }

  return { runId: runs[0]?.runId ?? null, runs };
}
