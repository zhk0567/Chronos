import { useCallback, useEffect, useState } from 'react';
import type { ImportPreview, ImportResult, SyncResult } from '../types/analysis';

export default function ImportPage() {
  const currentYear = new Date().getFullYear();
  const [summary, setSummary] = useState({
    count: 0,
    firstDate: null as string | null,
    lastDate: null as string | null,
    year: currentYear,
  });
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    const s = await window.chronosAPI.getEntrySummary();
    setSummary(s);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handlePickImport = async () => {
    setError('');
    const path = await window.chronosAPI.pickImportPath();
    if (!path) return;
    const p = await window.chronosAPI.previewImport(path);
    setPreview(p);
  };

  const handleImport = async () => {
    if (!preview) return;
    setLoading(true);
    setError('');
    try {
      const r = await window.chronosAPI.importFromPath(preview.source);
      setResult(r);
      setSyncResult(null);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleImportEcho = async () => {
    setError('');
    const path = await window.chronosAPI.pickEchoPath();
    if (!path) return;
    setLoading(true);
    try {
      const p = await window.chronosAPI.previewImport(path + '\\entries');
      setPreview(p);
      const r = await window.chronosAPI.importFromEcho(path);
      setResult(r);
      setSyncResult(null);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSyncEcho = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await window.chronosAPI.syncFromEcho();
      setSyncResult(r);
      setResult(null);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h2>日记导入</h2>
      <p className="hint">
        仅导入与分析 <strong>{currentYear}</strong> 年的日记。数据保存在本地 <code>data/entries/</code>
      </p>

      <div className="card stats-card">
        <h3>当前数据（{summary.year} 年）</h3>
        <p>
          已就绪 <strong>{summary.count}</strong> 篇日记
        </p>
        {summary.firstDate && (
          <p className="meta">
            日期范围：{summary.firstDate} — {summary.lastDate}
          </p>
        )}
      </div>

      <div className="actions">
        <button type="button" onClick={handleSyncEcho} disabled={loading}>
          同步 Echo 今年日记
        </button>
        <button type="button" onClick={handlePickImport} disabled={loading}>
          选择文件或目录
        </button>
        <button type="button" className="secondary" onClick={handleImportEcho} disabled={loading}>
          从 Echo 导入
        </button>
      </div>

      {syncResult && (
        <div className="card success">
          <p>
            同步完成：{syncResult.year} 年 {syncResult.synced} 篇已写入本地
            {syncResult.removed > 0 && `，已清理 ${syncResult.removed} 篇非今年数据`}
          </p>
          {syncResult.echoRoot && (
            <p className="meta">来源：{syncResult.echoRoot}</p>
          )}
        </div>
      )}

      {preview && (
        <div className="card">
          <h3>导入预览（仅 {preview.year ?? currentYear} 年）</h3>
          <p>来源：{preview.source}</p>
          <p>条目数：{preview.count}</p>
          {preview.firstDate && (
            <p>
              日期：{preview.firstDate} — {preview.lastDate}
            </p>
          )}
          {!preview.source.includes('entries') && (
            <button type="button" onClick={handleImport} disabled={loading}>
              {loading ? '导入中…' : '确认导入'}
            </button>
          )}
        </div>
      )}

      {result && (
        <div className="card success">
          <p>
            导入完成：新增 {result.imported} 篇，跳过 {result.skipped} 篇（非今年或已存在）
          </p>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
