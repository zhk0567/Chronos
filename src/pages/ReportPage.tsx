import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import type { AnalysisRunSummary, InsightReport } from '../types/analysis';
import { resolveRunId } from '../utils/runSelection';
import ReportSectionView from '../components/report/ReportSectionView';
import EvidencePanel from '../components/report/EvidencePanel';

export default function ReportPage() {
  const location = useLocation();
  const navRunId = (location.state as { runId?: string })?.runId ?? null;
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(navRunId);
  const [report, setReport] = useState<InsightReport | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);

  const loadRuns = useCallback(async () => {
    const { runId, runs: list } = await resolveRunId(navRunId, selectedRunId);
    setRuns(list);
    if (runId && runId !== selectedRunId) {
      setSelectedRunId(runId);
    }
  }, [navRunId, selectedRunId]);

  const loadReport = useCallback(async (runId: string) => {
    setLoading(true);
    const r = await window.chronosAPI.getReport(runId);
    setReport(r);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (selectedRunId) loadReport(selectedRunId);
  }, [selectedRunId, loadReport]);

  const handleExportHtml = async () => {
    if (!selectedRunId) return;
    const html = await window.chronosAPI.exportReportHtml(selectedRunId);
    if (html) await window.chronosAPI.saveExport(html, `chronos-report-${selectedRunId}.html`);
  };

  const handleExportJson = async () => {
    if (!selectedRunId) return;
    const json = await window.chronosAPI.exportReportJson(selectedRunId);
    if (json) await window.chronosAPI.saveExport(json, `chronos-report-${selectedRunId}.json`);
  };

  if (!report && loading) {
    return (
      <div className="page">
        <header className="page-header"><h2>洞察报告</h2></header>
        <p className="hint">加载报告…</p>
      </div>
    );
  }
  if (!report) {
    return (
      <div className="page">
        <header className="page-header">
          <h2>洞察报告</h2>
          <p className="hint">基于分析结果生成的结构化心理健康洞察。</p>
        </header>
        <div className="empty-state">
          <p className="hint">暂无报告，请先在「分析」页运行分析。</p>
        </div>
      </div>
    );
  }

  const tabs = report.sections;

  return (
    <div className="page report-page">
      <header className="page-header report-header">
        <div>
          <h2>洞察报告</h2>
          <p className="meta">
            {report.dateRange.start} — {report.dateRange.end} · {report.entryCount} 篇日记 ·
            生成于 {report.generatedAt.slice(0, 19)}
          </p>
        </div>
        <div className="report-actions">
          <select
            value={selectedRunId ?? ''}
            onChange={(e) => setSelectedRunId(e.target.value)}
          >
            {runs.map((r) => (
              <option key={r.runId} value={r.runId}>
                {r.runId} ({r.entryCount} 篇)
              </option>
            ))}
          </select>
          <button type="button" className="secondary" onClick={handleExportHtml}>
            导出 HTML
          </button>
          <button type="button" className="secondary" onClick={handleExportJson}>
            导出 JSON
          </button>
        </div>
      </header>

      {Object.keys(report.dataCompleteness).length > 0 && (
        <div className="card completeness-bar">
          <h3>数据完整性</h3>
          <ul className="completeness-list">
            {Object.entries(report.dataCompleteness).map(([k, v]) => (
              <li key={k} className="completeness-item">
                <div className="completeness-label">
                  <span>{k}</span>
                  <span>{Math.round(v * 100)}%</span>
                </div>
                <div className="completeness-track">
                  <div className="completeness-fill" style={{ width: `${Math.round(v * 100)}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="report-tabs">
        {tabs.map((section, i) => (
          <button
            key={section.id}
            type="button"
            className={activeTab === i ? 'active' : ''}
            onClick={() => setActiveTab(i)}
          >
            {section.title}
          </button>
        ))}
        <button
          type="button"
          className={activeTab === tabs.length ? 'active' : ''}
          onClick={() => setActiveTab(tabs.length)}
        >
          锚点 ({report.anchors.length})
        </button>
      </div>

      {activeTab < tabs.length ? (
        <ReportSectionView section={tabs[activeTab]} />
      ) : (
        <div className="anchors-panel">
          {report.anchors.length === 0 ? (
            <p>未检测到显著锚点</p>
          ) : (
            report.anchors.map((anchor) => (
              <div key={anchor.id} className="anchor-card">
                <div className="anchor-meta">
                  <span className="anchor-type">{anchor.emergenceType}</span>
                  <span className="anchor-date">{anchor.date}</span>
                </div>
                <h4>{anchor.title}</h4>
                <p>{anchor.description}</p>
                <p className="confidence">置信度 {Math.round(anchor.confidence * 100)}%</p>
                <EvidencePanel evidence={anchor.evidence} />
              </div>
            ))
          )}
        </div>
      )}

      {report.limitations.length > 0 && (
        <div className="card limitations">
          <h3>局限声明</h3>
          <ul>
            {report.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      )}

      {selectedRunId && (
        <div className="card narrative-links">
          <h3>三期叙事模块</h3>
          <div className="button-row">
            <Link to="/story" state={{ runId: selectedRunId }} className="nav-link-btn">
              生命故事{report.lifeStory?.lines?.length ? ` (${report.lifeStory.lines.length} 条)` : ''}
            </Link>
            <Link to="/selves" state={{ runId: selectedRunId }} className="nav-link-btn">
              多元自我
            </Link>
            <Link to="/reframe" state={{ runId: selectedRunId }} className="nav-link-btn">
              叙事重构{report.reframeCandidates?.length ? ` (${report.reframeCandidates.length})` : ''}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
