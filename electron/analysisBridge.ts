import fs from 'fs';
import path from 'path';
import type {
  AnalysisProgress,
  AnalysisRunSummary,
  DiaryEntry,
  InsightReport,
  LifeStoryBook,
  ReframeCandidate,
  ReframeSession,
  SelfVoiceMap,
} from '../src/types/analysis';
import type { PythonManager } from './pythonManager';
import { getSettings } from './settingsStore';

export class AnalysisBridge {
  constructor(
    private readonly python: PythonManager,
    private readonly appRoot: string
  ) {}

  private runsDir(): string {
    return path.join(this.appRoot, 'data', 'analysis', 'runs');
  }

  listRuns(): AnalysisRunSummary[] {
    const dir = this.runsDir();
    if (!fs.existsSync(dir)) return [];
    const runs: AnalysisRunSummary[] = [];
    for (const runId of fs.readdirSync(dir)) {
      const metaPath = path.join(dir, runId, 'meta.json');
      if (fs.existsSync(metaPath)) {
        try {
          runs.push(JSON.parse(fs.readFileSync(metaPath, 'utf-8')) as AnalysisRunSummary);
        } catch {
          /* skip */
        }
      }
    }
    runs.sort((a, b) => {
      const aDone = a.completedAt ?? a.startedAt;
      const bDone = b.completedAt ?? b.startedAt;
      return bDone.localeCompare(aDone);
    });
    const preferred = getSettings(this.appRoot).defaultRunId;
    if (preferred) {
      const idx = runs.findIndex((r) => r.runId === preferred);
      if (idx > 0) {
        const [pinned] = runs.splice(idx, 1);
        runs.unshift(pinned);
      }
    }
    return runs;
  }

  getDefaultRunId(): string | null {
    const runs = this.listRuns();
    const completed = runs.filter((r) => r.status === 'completed');
    const preferred = getSettings(this.appRoot).defaultRunId;
    if (preferred && completed.some((r) => r.runId === preferred)) {
      return preferred;
    }
    return completed[0]?.runId ?? runs[0]?.runId ?? null;
  }

  getReport(runId: string): InsightReport | null {
    const reportPath = path.join(this.runsDir(), runId, 'report.json');
    if (!fs.existsSync(reportPath)) return null;
    return JSON.parse(fs.readFileSync(reportPath, 'utf-8')) as InsightReport;
  }

  async startAnalysis(
    entries: DiaryEntry[],
    model: string,
    onProgress?: (p: AnalysisProgress) => void
  ): Promise<InsightReport> {
    const runId = `run_${Date.now()}`;

    const runOnce = async (): Promise<InsightReport> => {
      await this.python.ensureReady();
      const url = `${this.python.baseUrl}/analyze`;

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify({ runId, entries, model }),
        signal: AbortSignal.timeout(30 * 60 * 1000),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`分析失败: ${errText}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('分析引擎无响应');

      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let report: InsightReport | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = JSON.parse(line.slice(6)) as
            | { type: 'progress'; data: AnalysisProgress }
            | { type: 'complete'; data: InsightReport }
            | { type: 'error'; data: { message: string } };

          if (payload.type === 'progress') {
            onProgress?.(payload.data);
          } else if (payload.type === 'complete') {
            report = payload.data;
          } else if (payload.type === 'error') {
            throw new Error(payload.data.message);
          }
        }
      }

      if (!report) throw new Error('分析未返回报告');
      return report;
    };

    try {
      return await runOnce();
    } catch (err) {
      const msg = String(err);
      const retryable =
        msg.includes('ECONNRESET') ||
        msg.includes('terminated') ||
        msg.includes('Engine stopped') ||
        msg.includes('fetch failed');

      if (!retryable) throw err;

      await this.python.stop();
      await this.python.ensureReady();
      return runOnce();
    }
  }

  exportReportHtml(runId: string): string | null {
    const htmlPath = path.join(this.runsDir(), runId, 'report.html');
    if (!fs.existsSync(htmlPath)) return null;
    return fs.readFileSync(htmlPath, 'utf-8');
  }

  exportReportJson(runId: string): string | null {
    const jsonPath = path.join(this.runsDir(), runId, 'report.json');
    if (!fs.existsSync(jsonPath)) return null;
    return fs.readFileSync(jsonPath, 'utf-8');
  }

  async reframeStart(runId: string, candidateId: string, model: string): Promise<ReframeSession> {
    await this.python.ensureReady();
    const res = await fetch(`${this.python.baseUrl}/reframe/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ runId, candidateId, model }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<ReframeSession>;
  }

  async reframeMessage(
    sessionId: string,
    runId: string,
    candidateId: string,
    message: string,
    model: string
  ): Promise<ReframeSession> {
    await this.python.ensureReady();
    const res = await fetch(`${this.python.baseUrl}/reframe/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ sessionId, runId, candidateId, message, model }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<ReframeSession>;
  }

  async reframeFinalize(sessionId: string, model: string): Promise<ReframeSession> {
    await this.python.ensureReady();
    const res = await fetch(`${this.python.baseUrl}/reframe/finalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ sessionId, model }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<ReframeSession>;
  }
}
