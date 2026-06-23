import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import type { AnalysisRunSummary, ReframeCandidate, ReframeSession } from '../types/analysis';
import { resolveRunId } from '../utils/runSelection';

const DEFAULT_MODEL = 'minimax-m3:cloud';

export default function ReframePage() {
  const location = useLocation();
  const navRunId = (location.state as { runId?: string })?.runId ?? null;

  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(navRunId);
  const [candidates, setCandidates] = useState<ReframeCandidate[]>([]);
  const [session, setSession] = useState<ReframeSession | null>(null);
  const [activeCandidate, setActiveCandidate] = useState<ReframeCandidate | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadRuns = useCallback(async () => {
    const { runId: resolved, runs: list } = await resolveRunId(navRunId, runId, true);
    setRuns(list);
    if (resolved && resolved !== runId) setRunId(resolved);
  }, [navRunId, runId]);

  const loadCandidates = useCallback(async (id: string) => {
    setCandidates(await window.chronosAPI.listReframeCandidates(id));
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (runId) loadCandidates(runId);
  }, [runId, loadCandidates]);

  const startDialogue = async (candidate: ReframeCandidate) => {
    if (!runId) return;
    setLoading(true);
    setError('');
    try {
      const s = await window.chronosAPI.reframeStart(runId, candidate.id, DEFAULT_MODEL);
      setSession(s);
      setActiveCandidate(candidate);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!session || !runId || !activeCandidate || !input.trim()) return;
    setLoading(true);
    setError('');
    try {
      const s = await window.chronosAPI.reframeMessage(
        session.id,
        runId,
        activeCandidate.id,
        input.trim(),
        DEFAULT_MODEL
      );
      setSession(s);
      setInput('');
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const finalize = async () => {
    if (!session) return;
    setLoading(true);
    try {
      const s = await window.chronosAPI.reframeFinalize(session.id, DEFAULT_MODEL);
      setSession(s);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page reframe-page">
      <header className="page-header">
        <h2>叙事重构</h2>
        <p className="hint">
          识别内化问题叙事，通过引导性提问探索替代解读。系统仅提供镜子和提问，不做诊断或建议。
        </p>
      </header>

      <select value={runId ?? ''} onChange={(e) => { setRunId(e.target.value); setSession(null); }}>
        {runs.map((r) => (
          <option key={r.runId} value={r.runId}>{r.runId}</option>
        ))}
      </select>

      {!session && (
        <div className="card">
          <h3>可探索的问题叙事</h3>
          {candidates.length === 0 && <p className="hint">暂无检测到重复的问题叙事模式。</p>}
          {candidates.map((c) => (
            <div key={c.id} className="reframe-candidate">
              <p><strong>「{c.problemStatement}」</strong></p>
              <p className="meta">模式：{c.internalizedPattern} · 出现 {c.frequency} 次</p>
              {c.exceptionMoments.length > 0 && (
                <div>
                  <p className="meta">例外时刻：</p>
                  <ul>
                    {c.exceptionMoments.map((e, i) => (
                      <li key={i}><span className="ev-date">{e.date}</span> {e.text}</li>
                    ))}
                  </ul>
                </div>
              )}
              <button type="button" disabled={loading} onClick={() => startDialogue(c)}>
                发起重构对话
              </button>
            </div>
          ))}
        </div>
      )}

      {session && (
        <div className="card reframe-dialogue">
          <h3>重构对话</h3>
          <p className="meta">原叙述：{session.originalNarrative}</p>

          <div className="chat-messages">
            {session.messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.role}`}>
                <span className="chat-role">{m.role === 'guide' ? '引导' : '你'}</span>
                <p>{m.text}</p>
              </div>
            ))}
          </div>

          {!session.alternativeStory && (
            <div className="chat-input">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="写下你的想法…"
                rows={3}
              />
              <div className="button-row">
                <button type="button" disabled={loading || !input.trim()} onClick={sendMessage}>
                  发送
                </button>
                <button type="button" className="secondary" disabled={loading} onClick={finalize}>
                  结束并生成替代故事
                </button>
                <button type="button" className="secondary" onClick={() => setSession(null)}>
                  返回列表
                </button>
              </div>
            </div>
          )}

          {session.alternativeStory && (
            <div className="reframe-comparison">
              <div className="comparison-col">
                <h4>原来的叙述</h4>
                <p>{session.originalNarrative}</p>
              </div>
              <div className="comparison-col">
                <h4>替代故事 <span className="meta">(系统推断)</span></h4>
                <p>{session.alternativeStory}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
