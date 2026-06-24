import { useCallback, useEffect, useState } from 'react';
import type { ColumnMapping, ContextImportResult, CsvPreview } from '../types/analysis';

type ImportType = 'apple_health' | 'wearable_csv' | 'screen_time' | 'gpx' | 'manual_location';

const ADVANCED_IMPORT_OPTIONS: { type: ImportType; label: string; hint: string; needsMapping?: boolean }[] = [
  { type: 'apple_health', label: 'Apple Health (export.xml)', hint: '步数、睡眠时长、静息心率' },
  { type: 'wearable_csv', label: '可穿戴 CSV', hint: '支持自定义列映射', needsMapping: true },
  { type: 'screen_time', label: '屏幕时间 CSV', hint: '支持自定义列映射', needsMapping: true },
  { type: 'gpx', label: 'GPX 轨迹', hint: '日级主要地点聚合' },
  { type: 'manual_location', label: '手动地点 JSON', hint: 'JSON 数组或下方表单直接录入' },
];

const WEARABLE_FIELDS: { key: keyof ColumnMapping; label: string }[] = [
  { key: 'date', label: '日期列' },
  { key: 'steps', label: '步数列' },
  { key: 'sleep', label: '睡眠列' },
  { key: 'hr', label: '心率列' },
];

const SCREEN_FIELDS: { key: keyof ColumnMapping; label: string }[] = [
  { key: 'date', label: '日期列' },
  { key: 'minutes', label: '时长列（分钟）' },
  { key: 'app', label: '应用列' },
];

function guessMapping(headers: string[], type: ImportType): ColumnMapping {
  const lower = headers.map((h) => h.toLowerCase());
  const find = (...candidates: string[]) => {
    for (const c of candidates) {
      const idx = lower.findIndex((h) => h === c || h.includes(c));
      if (idx >= 0) return headers[idx];
    }
    return '';
  };
  if (type === 'wearable_csv') {
    return {
      date: find('date', '日期', 'day'),
      steps: find('steps', '步数', 'step'),
      sleep: find('sleep', '睡眠'),
      hr: find('hr', 'heart', '心率'),
    };
  }
  return {
    date: find('date', '日期'),
    minutes: find('minutes', 'duration', '时长', 'screentime'),
    app: find('app', '应用'),
  };
}

export default function DataSourcesPage() {
  const [sources, setSources] = useState<Record<string, number>>({});
  const [lastImport, setLastImport] = useState<ContextImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const [mappingOpen, setMappingOpen] = useState(false);
  const [pendingType, setPendingType] = useState<ImportType | null>(null);
  const [pendingPath, setPendingPath] = useState('');
  const [csvPreview, setCsvPreview] = useState<CsvPreview | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>({});

  const [locDate, setLocDate] = useState('');
  const [locPlace, setLocPlace] = useState('');
  const [locType, setLocType] = useState('home');

  const refresh = useCallback(async () => {
    setSources(await window.chronosAPI.listContextSources());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const runImport = async (type: ImportType, path: string, colMapping?: ColumnMapping) => {
    setLoading(true);
    setError('');
    try {
      const result = await window.chronosAPI.importContext(path, type, colMapping);
      setLastImport(result);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async (type: ImportType, needsMapping?: boolean) => {
    setError('');
    const path = await window.chronosAPI.pickContextFile(type);
    if (!path) return;

    if (needsMapping) {
      const preview = await window.chronosAPI.previewCsv(path);
      setPendingType(type);
      setPendingPath(path);
      setCsvPreview(preview);
      setMapping(guessMapping(preview.headers, type));
      setMappingOpen(true);
      return;
    }

    await runImport(type, path);
  };

  const confirmMappingImport = async () => {
    if (!pendingType || !pendingPath) return;
    setMappingOpen(false);
    await runImport(pendingType, pendingPath, mapping);
    setPendingType(null);
    setPendingPath('');
    setCsvPreview(null);
  };

  const handleSaveLocation = async () => {
    if (!locDate || !locPlace.trim()) {
      setError('请填写日期和地点名称');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await window.chronosAPI.saveManualLocation(locDate, locPlace.trim(), locType);
      setLastImport({ type: 'manual_location', daysImported: 1, source: 'form' });
      setLocDate('');
      setLocPlace('');
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const mappingFields = pendingType === 'screen_time' ? SCREEN_FIELDS : WEARABLE_FIELDS;

  return (
    <div className="page">
      <header className="page-header">
        <h2>数据源</h2>
        <p className="hint">
          Chronos 以<strong>日记</strong>为核心；天气在「设置」中配置常驻城市后，分析时自动拉取。
          下方扩展数据源一般无需导入。
        </p>
      </header>

      <div className="card stats-card">
        <h3>已缓存天气数据</h3>
        <p className="meta">天气：{sources.weather ?? 0} 天（相对日记日期范围统计见设置页）</p>
        {(sources.wearable ?? 0) + (sources.digital ?? 0) + (sources.location ?? 0) > 0 && (
          <p className="meta">
            扩展数据：可穿戴 {sources.wearable ?? 0} 天 · 数字行为 {sources.digital ?? 0} 天 · 位置{' '}
            {sources.location ?? 0} 天
          </p>
        )}
      </div>

      <div className="card">
        <button type="button" className="secondary" onClick={() => setAdvancedOpen(!advancedOpen)}>
          {advancedOpen ? '收起可选扩展数据源' : '展开可选扩展数据源（一般无需）'}
        </button>
      </div>

      {advancedOpen && (
        <>
          <div className="import-grid">
            {ADVANCED_IMPORT_OPTIONS.map((opt) => (
              <div key={opt.type} className="card import-option">
                <h4>{opt.label}</h4>
                <p className="meta">{opt.hint}</p>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleImport(opt.type, opt.needsMapping)}
                >
                  选择文件导入
                </button>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>手动录入地点</h3>
            <p className="meta">无需 JSON 文件，直接写入 location 缓存</p>
            <div className="form-grid">
              <label className="field">
                日期
                <input type="date" value={locDate} onChange={(e) => setLocDate(e.target.value)} />
              </label>
              <label className="field">
                地点名称
                <input
                  type="text"
                  value={locPlace}
                  onChange={(e) => setLocPlace(e.target.value)}
                  placeholder="例如：公司、家、咖啡厅"
                />
              </label>
              <label className="field">
                类型
                <select value={locType} onChange={(e) => setLocType(e.target.value)}>
                  <option value="home">home</option>
                  <option value="work">work</option>
                  <option value="social">social</option>
                  <option value="outdoor">outdoor</option>
                  <option value="other">other</option>
                </select>
              </label>
            </div>
            <button type="button" disabled={loading} onClick={handleSaveLocation}>
              保存地点
            </button>
          </div>
        </>
      )}

      {mappingOpen && csvPreview && (
        <div className="modal-overlay">
          <div className="card modal">
            <h3>CSV 列映射</h3>
            <p className="meta">为每列选择对应字段，预览前 3 行数据</p>
            {mappingFields.map(({ key, label }) => (
              <label key={key} className="field">
                {label}
                <select
                  value={mapping[key] ?? ''}
                  onChange={(e) => setMapping((m) => ({ ...m, [key]: e.target.value }))}
                >
                  <option value="">（跳过）</option>
                  {csvPreview.headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            {csvPreview.rows.length > 0 && (
              <div className="csv-preview">
                <h4>预览</h4>
                <table>
                  <thead>
                    <tr>
                      {csvPreview.headers.map((h) => (
                        <th key={h}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {csvPreview.rows.map((row, i) => (
                      <tr key={i}>
                        {csvPreview.headers.map((h) => (
                          <td key={h}>{row[h]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="button-row">
              <button type="button" onClick={confirmMappingImport} disabled={!mapping.date}>
                确认导入
              </button>
              <button type="button" className="secondary" onClick={() => setMappingOpen(false)}>
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {lastImport && (
        <div className="card success">
          <p>导入完成：{lastImport.daysImported} 天数据已写入本地 context 目录</p>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
