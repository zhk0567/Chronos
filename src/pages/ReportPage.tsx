import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import type { AnalysisRunSummary, InsightReport } from '../types/analysis';
import ReportSectionView from '../components/report/ReportSectionView';
import EvidencePanel from '../components/report/EvidencePanel';

export default function ReportPage() {
  const location = useLocation();
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    (location.state as { runId?: string })?.runId ?? null
  );
  const [report, setReport] = useState<InsightReport | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);

  const loadRuns = useCallback(async () => {
    const list = await window.chronosAPI.listRuns();
    setRuns(list);
    if (!selectedRunId && list.length > 0) {
      setSelectedRunId(list[0].runId);
    }
  }, [selectedRunId]);

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

  if (!report && loading) return <div className="page"><p>加载报告…</p></div>;
  if (!report) {
    return (
      <div className="page">
        <h2>洞察报告</h2>
        <p className="hint">暂无报告，请先在「分析」页运行分析。</p>
      </div>
    );
  }

  const tabs = report.sections;

  return (
    <div className="page report-page">
      <div className="report-header">
        <h2>洞察报告</h2>
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
      </div>

      <p className="meta">
        {report.dateRange.start} — {report.dateRange.end} · {report.entryCount} 篇日记 ·
        生成于 {report.generatedAt.slice(0, 19)}
      </p>

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
    </div>
  );
}
