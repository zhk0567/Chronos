import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AnalysisProgress, AnalysisRunSummary, EngineHealth } from '../types/analysis';

const DEFAULT_MODEL = 'gemma3:4b';

const STEP_LABELS: Record<string, string> = {
  extract: '形态分类与信息抽取',
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

  const refresh = useCallback(async () => {
    setHealth(await window.chronosAPI.getEngineHealth());
    setSummary(await window.chronosAPI.getEntrySummary());
    setRuns(await window.chronosAPI.listRuns());
  }, []);

  useEffect(() => {
    refresh();
    const unsub = window.chronosAPI.onAnalysisProgress((p) => setProgress(p));
    return unsub;
  }, [refresh]);

  const handleAnalyze = async () => {
    if (summary.count === 0) {
      setError(`没有 ${summary.year} 年的日记，请先在「导入」页同步或导入`);
      return;
    }
    setRunning(true);
    setError('');
    setProgress(null);
    try {
      const report = await window.chronosAPI.startAnalysis(model);
      await refresh();
      navigate('/report', { state: { runId: report.runId } });
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
      setProgress(null);
    }
  };

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
        <button type="button" onClick={handleAnalyze} disabled={running || summary.count === 0}>
          {running ? '分析中…' : '开始分析'}
        </button>
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
