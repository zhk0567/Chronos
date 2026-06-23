import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import type { AnalysisRunSummary, SelfVoiceMap } from '../types/analysis';
import { resolveRunId } from '../utils/runSelection';

const VOICE_COLORS: Record<string, string> = {
  critic: '#9e6b6b',
  comforter: '#5d8a6a',
  dreamer: '#5d7aa6',
  observer: '#8a7a5d',
  other: '#8a8580',
};

const VOICE_LABELS: Record<string, string> = {
  critic: '批评者',
  comforter: '安慰者',
  dreamer: '梦想家',
  observer: '观察者',
  other: '其他',
};

export default function SelvesPage() {
  const location = useLocation();
  const navRunId = (location.state as { runId?: string })?.runId ?? null;

  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(navRunId);
  const [map, setMap] = useState<SelfVoiceMap | null>(null);

  const loadRuns = useCallback(async () => {
    const { runId: resolved, runs: list } = await resolveRunId(navRunId, runId, true);
    setRuns(list);
    if (resolved && resolved !== runId) setRunId(resolved);
  }, [navRunId, runId]);

  const loadMap = useCallback(async (id: string) => {
    setMap(await window.chronosAPI.getSelfVoiceMap(id));
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (runId) loadMap(runId);
  }, [runId, loadMap]);

  if (!map || map.profiles.length === 0) {
    return (
      <div className="page">
        <header className="page-header">
          <h2>多元自我</h2>
          <p className="hint">从内省型日记中识别的内部声音及其时间演化。</p>
        </header>
        <div className="empty-state">
          <p className="hint">内省型日记数据不足，暂无法构建自我声音图谱。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page selves-page">
      <header className="page-header">
        <h2>多元自我</h2>
        <p className="hint">从内省型日记中识别的内部声音及其时间演化。</p>
      </header>

      <select value={runId ?? ''} onChange={(e) => setRunId(e.target.value)}>
        {runs.map((r) => (
          <option key={r.runId} value={r.runId}>{r.runId}</option>
        ))}
      </select>

      <div className="card">
        <h3>自我星盘</h3>
        <svg viewBox="0 0 1 1" className="star-chart">
          {map.starLayout.map((p) => (
            <g key={p.voiceType}>
              <circle
                cx={p.x}
                cy={p.y}
                r={0.06}
                fill={VOICE_COLORS[p.voiceType] ?? '#999'}
              />
              <text x={p.x} y={p.y + 0.1} textAnchor="middle" fontSize="0.05" fill="#7a756c">
                {VOICE_LABELS[p.voiceType] ?? p.voiceType}
              </text>
            </g>
          ))}
        </svg>
      </div>

      <div className="card">
        <h3>声音画像</h3>
        <ul className="voice-profiles">
          {map.profiles.map((p) => (
            <li key={p.voiceType}>
              <strong style={{ color: VOICE_COLORS[p.voiceType] }}>{p.label}</strong>
              <span className="meta"> — {p.mentionCount} 次</span>
              <p>{p.description}</p>
              {p.sampleQuotes.slice(0, 2).map((q, i) => (
                <blockquote key={i}>{q}</blockquote>
              ))}
            </li>
          ))}
        </ul>
      </div>

      {map.timeline.length > 0 && (
        <div className="card">
          <h3>对话河流（按月采样）</h3>
          <div className="river-chart">
            {map.timeline.filter((_, i) => i % Math.max(1, Math.floor(map.timeline.length / 12)) === 0).map((pt) => (
              <div key={pt.date} className="river-bar" title={pt.date}>
                {Object.entries(pt.proportions).map(([v, pct]) => (
                  <div
                    key={v}
                    style={{
                      height: `${pct * 60}px`,
                      background: VOICE_COLORS[v] ?? '#ccc',
                      width: '12px',
                      display: 'inline-block',
                      margin: '0 1px',
                    }}
                  />
                ))}
                <span className="river-label">{pt.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {map.transitions.length > 0 && (
        <div className="card">
          <h3>声音转换模式</h3>
          <ul>
            {map.transitions.map((t, i) => (
              <li key={i}>{t.description}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
