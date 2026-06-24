import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AnalysisProgress, AnalysisRunSummary, BenchmarkResult, BenchmarkSuiteResult, EngineHealth } from '../types/analysis';

const DEFAULT_MODEL = 'gemma3:4b';

const STEP_LABELS: Record<string, string> = {  extract: '形态分类与信息抽取',
  emotion: '情绪评分',
  context: '语境数据加载',
  align: '多源对齐',
  anchors: '锚点涌现',
  factors: '控制变量因素分析',
  network: '关系网络',
  interaction: '交互效应',
  environment: '环境敏感性',
  physio: '生理-心理耦合',
  warning: '预警模式',
  language: '语言模式',
  themes: '主题分析',
  chains: '锚点关联链',
  story: '生命故事',
  selves: '多元自我',
  reframe: '问题叙事识别',
  report: '报告生成',
};

export default function AnalysisPage() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [summary, setSummary] = useState({
    count: 0,
    firstDate: null as string | null,
    lastDate: null as string | null,
    year: new Date().getFullYear(),
  });
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [error, setError] = useState('');
  const [benchmarkSuite, setBenchmarkSuite] = useState<BenchmarkSuiteResult | null>(null);
  const [benchmarkRunning, setBenchmarkRunning] = useState(false);

  const refresh = useCallback(async () => {
    setHealth(await window.chronosAPI.getEngineHealth());
    setSummary(await window.chronosAPI.getEntrySummary());
    setRuns(await window.chronosAPI.listRuns());
    setBenchmarkSuite(await window.chronosAPI.getLastBenchmarkSuite());
  }, []);

  useEffect(() => {
    refresh();
    const unsub = window.chronosAPI.onAnalysisProgress((p) => setProgress(p));
    return unsub;
  }, [refresh]);

  const handleAnalyze = async (resumeRunId?: string) => {
    if (summary.count === 0) {
      setError(`没有 ${summary.year} 年的日记，请先在「导入」页同步或导入`);
      return;
    }
    setRunning(true);
    setError('');
    setProgress(null);
    try {
      const report = await window.chronosAPI.startAnalysis(model, resumeRunId ?? null);
      await refresh();
      navigate('/report', { state: { runId: report.runId } });
    } catch (e) {
      const msg = String(e);
      setError(msg.includes('分析已取消') ? '分析已取消，可在下方点击「继续分析」' : msg);
    } finally {
      setRunning(false);
      setProgress(null);
    }
  };

  const handleCancel = async () => {
    setError('');
    await window.chronosAPI.cancelAnalysis();
    await refresh();
  };

  const handleDiscardRun = async (runId: string) => {
    if (!window.confirm(`确定放弃并删除未完成分析 ${runId}？此操作不可恢复。`)) return;
    setError('');
    try {
      await window.chronosAPI.deleteAnalysisRun(runId);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const pausableRuns = runs.filter(
    (r) => (r.status === 'paused' || r.status === 'cancelled') && r.lastCompletedStep
  );

  const handleRunBenchmark = async () => {
    setBenchmarkRunning(true);
    setError('');
    try {
      setBenchmarkSuite(await window.chronosAPI.runBenchmark());
    } catch (e) {
      setError(String(e));
    } finally {
      setBenchmarkRunning(false);
    }
  };

  const fmtMetric = (m: BenchmarkResult['anchor']) =>
    `P ${(m.precision * 100).toFixed(0)}% · R ${(m.recall * 100).toFixed(0)}% · F1 ${(m.f1 * 100).toFixed(0)}%`;

  return (
    <div className="page">
      <header className="page-header">
        <h2>分析引擎</h2>
        <p className="hint">对今年全部日记运行 18 步分析流水线，生成洞察报告与叙事模块。</p>
      </header>

      <div className="card">
        <h3>引擎状态</h3>
        {health ? (
          <ul className="status-list">
            <li className={health.python ? 'ok' : 'fail'}>
              Python 引擎：{health.python ? '运行中' : '未启动'}
            </li>
            <li className={health.ollama ? 'ok' : 'warn'}>
              Ollama：{health.ollama ? `已连接 (${health.ollamaModel})` : '未连接（将使用启发式分析）'}
            </li>
          </ul>
        ) : (
          <p>检查中…</p>
        )}
        {health?.error && <p className="error">{health.error}</p>}
      </div>

      <div className="card">
        <h3>分析配置</h3>
        <p>
          {summary.year} 年日记：{summary.count} 篇
        </p>
        {summary.firstDate && (
          <p className="meta">
            {summary.firstDate} — {summary.lastDate}
          </p>
        )}
        <label className="field">
          Ollama 模型
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={running}
          />
        </label>
        <div className="button-row">
          <button type="button" onClick={() => handleAnalyze()} disabled={running || summary.count === 0}>
            {running ? '分析中…' : '开始分析'}
          </button>
          {running && (
            <button type="button" className="secondary danger" onClick={handleCancel}>
              取消分析
            </button>
          )}
        </div>
      </div>

      {progress && (
        <div className="card progress-card">
          <h3>{STEP_LABELS[progress.step] ?? progress.step}</h3>
          <p>{progress.message}</p>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress.percent}%` }} />
          </div>
          <p className="meta">
            步骤 {progress.stepIndex}/{progress.totalSteps}
          </p>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <div className="card">
        <h3>质量基准（冒烟测试）</h3>
        <p className="hint">
          在合成日记标注集上评估锚点/主题/关系网络与预警模式的召回与精确率（纯启发式，无需 Ollama）。当前含 demo、contradiction、intensity、warning 四套
          fixture。
        </p>
        <button type="button" className="secondary" disabled={benchmarkRunning} onClick={handleRunBenchmark}>
          {benchmarkRunning ? '运行中…' : '运行全部 benchmark'}
        </button>
        {benchmarkSuite && benchmarkSuite.fixtures.length > 0 && (
          <div className="benchmark-suite">
            <p className="meta">上次运行：{benchmarkSuite.ranAt.slice(0, 19)}</p>
            {benchmarkSuite.fixtures.map((benchmark) => (
              <ul key={benchmark.name} className="benchmark-metrics meta">
                <li>
                  <strong>{benchmark.name}</strong>（{benchmark.entryCount} 篇）
                </li>
                <li>
                  锚点：{fmtMetric(benchmark.anchor)} (tp={benchmark.anchor.tp} fp={benchmark.anchor.fp} fn=
                  {benchmark.anchor.fn})
                </li>
                <li>
                  主题：{fmtMetric(benchmark.theme)} (tp={benchmark.theme.tp} fp={benchmark.theme.fp} fn=
                  {benchmark.theme.fn})
                </li>
                <li>
                  关系：{fmtMetric(benchmark.relationship)} (tp={benchmark.relationship.tp} fp=
                  {benchmark.relationship.fp} fn={benchmark.relationship.fn})
                </li>
                {benchmark.warning && (
                  <li>
                    预警：{fmtMetric(benchmark.warning)} (tp={benchmark.warning.tp} fp={benchmark.warning.fp} fn=
                    {benchmark.warning.fn})
                    {typeof benchmark.details?.warningTargets === 'object' &&
                    benchmark.details.warningTargets !== null &&
                    'met' in (benchmark.details.warningTargets as object) ? (
                      <span>
                        {' '}
                        — 目标{' '}
                        {(benchmark.details.warningTargets as { met?: boolean }).met ? '已达成' : '未达成'}
                      </span>
                    ) : null}
                  </li>
                )}
              </ul>
            ))}
          </div>
        )}
      </div>

      {pausableRuns.length > 0 && (
        <div className="card">
          <h3>可继续的分析</h3>
          <p className="hint">
            以下分析未完成，可从上次步骤续跑（日记须与上次一致）。若不再需要，可「放弃并删除」以清理半成品产物。
          </p>
          <ul className="run-list">
            {pausableRuns.map((run) => (
              <li key={run.runId}>
                <span className="meta">{run.runId}</span>
                <span className="meta">
                  已完成至：{STEP_LABELS[run.lastCompletedStep ?? ''] ?? run.lastCompletedStep}
                </span>
                <button
                  type="button"
                  className="secondary"
                  disabled={running}
                  onClick={() => handleAnalyze(run.runId)}
                >
                  继续分析
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={running}
                  onClick={() => handleDiscardRun(run.runId)}
                >
                  放弃并删除
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {runs.length > 0 && (
        <div className="card">
          <h3>历史分析</h3>
          <ul className="run-list">
            {runs.map((run) => (
              <li key={run.runId}>
                <button
                  type="button"
                  className="link-btn"
                  onClick={() => navigate('/report', { state: { runId: run.runId } })}
                >
                  {run.runId}
                </button>
                <span className="meta">
                  {run.startedAt.slice(0, 19)} · {run.entryCount} 篇 · {run.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
