import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import type { AnalysisRunSummary, LifeStoryBook, NarrativeLine } from '../types/analysis';
import EmotionArcSparkline from '../components/story/EmotionArcSparkline';
import { resolveRunId } from '../utils/runSelection';

export default function StoryPage() {
  const location = useLocation();
  const navRunId = (location.state as { runId?: string })?.runId ?? null;
  const highlightAnchor = (location.state as { anchorId?: string })?.anchorId;

  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(navRunId);
  const [story, setStory] = useState<LifeStoryBook | null>(null);
  const [expandedLine, setExpandedLine] = useState<string | null>(null);
  const [noteInput, setNoteInput] = useState('');

  const loadRuns = useCallback(async () => {
    const { runId: resolved, runs: list } = await resolveRunId(navRunId, runId, true);
    setRuns(list);
    if (resolved && resolved !== runId) setRunId(resolved);
  }, [navRunId, runId]);

  const loadStory = useCallback(async (id: string) => {
    setStory(await window.chronosAPI.getStoryBook(id));
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (runId) loadStory(runId);
  }, [runId, loadStory]);

  const handleEdit = async (line: NarrativeLine, status: 'accepted' | 'rejected' | 'edited') => {
    if (!runId) return;
    await window.chronosAPI.saveStoryEdit(runId, line.id, status, noteInput || line.userNote || undefined);
    setNoteInput('');
    await loadStory(runId);
  };

  if (!story) {
    return (
      <div className="page">
        <header className="page-header">
          <h2>生命故事</h2>
          <p className="hint">基于锚点关联链梳理的叙事线。</p>
        </header>
        <div className="empty-state">
          <p className="hint">请先运行分析以生成叙事线。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page story-page">
      <header className="page-header">
        <h2>生命故事</h2>
        <p className="hint">基于锚点关联链梳理的叙事线。缺失细节处不会补写。</p>
      </header>

      <select value={runId ?? ''} onChange={(e) => setRunId(e.target.value)}>
        {runs.map((r) => (
          <option key={r.runId} value={r.runId}>
            {r.runId} ({r.entryCount} 篇)
          </option>
        ))}
      </select>

      {story.lines.filter((l) => l.status !== 'rejected').map((line) => (
        <div key={line.id} className={`card story-line status-${line.status}`}>
          <div className="story-line-header">
            <h3>{line.title}</h3>
            <span className="meta">{line.themeOrRelation}</span>
            {line.toneShift && <p className="meta">基调变化：{line.toneShift}</p>}
            {line.emotionArc.length >= 2 && <EmotionArcSparkline arc={line.emotionArc} />}
          </div>

          <button type="button" className="secondary" onClick={() => setExpandedLine(expandedLine === line.id ? null : line.id)}>
            {expandedLine === line.id ? '收起' : '展开时间轴'}
          </button>

          {expandedLine === line.id && (
            <ol className="story-timeline">
              {line.nodes.map((node) => (
                <li
                  key={node.anchorId}
                  className={highlightAnchor === node.anchorId ? 'highlight' : ''}
                >
                  <span className="story-date">{node.date}</span>
                  <strong>{node.title}</strong>
                  {node.emotionScore != null && (
                    <span className="meta"> 情绪 {node.emotionScore.toFixed(1)}</span>
                  )}
                  <p>{node.summary}</p>
                </li>
              ))}
            </ol>
          )}

          <div className="button-row">
            <button type="button" onClick={() => handleEdit(line, 'accepted')}>接受</button>
            <button type="button" className="secondary" onClick={() => handleEdit(line, 'rejected')}>拒绝</button>
          </div>
          <label className="field">
            标注
            <input
              type="text"
              value={noteInput}
              placeholder={line.userNote ?? '可选备注'}
              onChange={(e) => setNoteInput(e.target.value)}
            />
          </label>
          <button type="button" className="secondary" onClick={() => handleEdit(line, 'edited')}>
            保存标注
          </button>
        </div>
      ))}
    </div>
  );
}
