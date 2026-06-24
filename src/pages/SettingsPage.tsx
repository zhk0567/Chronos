import { useCallback, useEffect, useState } from 'react';
import type { ContextCompleteness, FeedbackSummary, ThemeMode, UserSettings, WeatherTestResult } from '../types/analysis';
import { applyTheme } from '../utils/theme';

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>({
    residentCity: '',
    latitude: null,
    longitude: null,
    timezone: 'Asia/Shanghai',
    theme: 'light' as ThemeMode,
  });
  const [completeness, setCompleteness] = useState<ContextCompleteness | null>(null);
  const [inventory, setInventory] = useState<{ entries: number; analysisRuns: number; contextFiles: number } | null>(
    null
  );
  const [cityInput, setCityInput] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [testing, setTesting] = useState(false);
  const [weatherTest, setWeatherTest] = useState<WeatherTestResult | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState('');
  const [deleteEntriesConfirm, setDeleteEntriesConfirm] = useState('');
  const [preserveAnonymizedAnalysis, setPreserveAnonymizedAnalysis] = useState(true);
  const [deletingEntries, setDeletingEntries] = useState(false);
  const [deleteEntriesResult, setDeleteEntriesResult] = useState('');
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary | null>(null);
  const [exportingFeedback, setExportingFeedback] = useState(false);

  const refresh = useCallback(async () => {
    const s = await window.chronosAPI.getSettings();
    setSettings(s);
    setCityInput(s.residentCity);
    setCompleteness(await window.chronosAPI.getContextCompleteness());
    setInventory(await window.chronosAPI.getDataInventory());
    setFeedbackSummary(await window.chronosAPI.getFeedbackSummary());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSave = async () => {
    setError('');
    setWeatherTest(null);
    try {
      const s = await window.chronosAPI.saveSettings({
        residentCity: cityInput.trim(),
        theme: settings.theme,
      });
      setSettings(s);
      applyTheme(s.theme ?? 'light');
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleTestWeather = async () => {
    setError('');
    setTesting(true);
    setWeatherTest(null);
    try {
      if (cityInput.trim() !== settings.residentCity) {
        await window.chronosAPI.saveSettings({ residentCity: cityInput.trim() });
        await refresh();
      }
      const result = await window.chronosAPI.testWeather();
      setWeatherTest(result);
      if (!result.ok) setError(result.error ?? '天气连接失败');
    } catch (e) {
      setError(String(e));
    } finally {
      setTesting(false);
    }
  };

  const handleExportFeedback = async () => {
    setError('');
    setExportingFeedback(true);
    try {
      const json = await window.chronosAPI.exportFeedbackJson();
      const ok = await window.chronosAPI.saveExport(
        json,
        `chronos-feedback-${new Date().toISOString().slice(0, 10)}.json`
      );
      if (!ok) setError('已取消导出');
    } catch (e) {
      setError(String(e));
    } finally {
      setExportingFeedback(false);
    }
  };

  const handleDeleteEntries = async () => {
    if (deleteEntriesConfirm !== '确认删除日记') {
      setError('请在下方输入「确认删除日记」以继续');
      return;
    }
    setError('');
    setDeletingEntries(true);
    setDeleteEntriesResult('');
    try {
      const result = await window.chronosAPI.deleteDiaryEntries({ preserveAnonymizedAnalysis });
      let msg = `已删除日记原文 ${result.deleted.entries} 篇`;
      if (result.preserveAnonymizedAnalysis) {
        msg +=
          `；已脱敏 ${result.deleted.runsAnonymized} 次分析` +
          `（移除 ${result.deleted.filesDeleted} 个含原文文件，改写 ${result.deleted.filesRedacted} 个产物）`;
        if (result.deleted.narrativeFiles > 0) {
          msg += `；清除叙事编辑 ${result.deleted.narrativeFiles} 个文件`;
        }
      } else {
        msg += '；分析产物未改动（仍可能含原文引用，建议勾选保留脱敏分析）';
      }
      setDeleteEntriesResult(msg);
      setDeleteEntriesConfirm('');
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setDeletingEntries(false);
    }
  };

  const handleDeleteAll = async () => {
    if (deleteConfirm !== '确认删除') {
      setError('请在下方输入「确认删除」以继续');
      return;
    }
    setError('');
    setDeleting(true);
    setDeleteResult('');
    try {
      const result = await window.chronosAPI.deleteAllUserData();
      setDeleteResult(
        `已删除：日记 ${result.deleted.entries} 篇、分析 run ${result.deleted.analysisRuns} 个、` +
          `语境文件 ${result.deleted.contextFiles} 个、叙事文件 ${result.deleted.narrativeFiles} 个`
      );
      setDeleteConfirm('');
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h2>设置</h2>
        <p className="hint">配置常驻城市以获取历史天气数据（Open-Meteo，仅传输坐标与日期，不含日记内容）</p>
      </header>

      <div className="card">
        <h3>常驻城市</h3>
        <label className="field">
          城市名称
          <input
            type="text"
            value={cityInput}
            onChange={(e) => setCityInput(e.target.value)}
            placeholder="例如：北京、上海、杭州"
          />
        </label>
        {settings.latitude != null && (
          <p className="meta">
            坐标：{settings.latitude.toFixed(4)}, {settings.longitude?.toFixed(4)}
          </p>
        )}
        <div className="button-row">
          <button type="button" onClick={handleSave}>
            {saved ? '已保存' : '保存'}
          </button>
          <button type="button" className="secondary" disabled={testing || !cityInput.trim()} onClick={handleTestWeather}>
            {testing ? '测试中…' : '测试天气连接'}
          </button>
        </div>
        {weatherTest?.ok && weatherTest.sampleTemp != null && (
          <p className="success-inline">
            连接成功：{weatherTest.date} 平均气温 {weatherTest.sampleTemp.toFixed(1)}°C
          </p>
        )}
      </div>

      <div className="card">
        <h3>外观</h3>
        <label className="field">
          主题
          <select
            value={settings.theme ?? 'light'}
            onChange={(e) => {
              const theme = e.target.value as ThemeMode;
              setSettings((prev) => ({ ...prev, theme }));
              applyTheme(theme);
            }}
          >
            <option value="light">浅色（护眼）</option>
            <option value="dark">深色</option>
            <option value="system">跟随系统</option>
          </select>
        </label>
        <p className="hint">主题变更在点击「保存」后持久化到本地设置。</p>
      </div>

      {completeness && (
        <div className="card">
          <h3>天气数据覆盖</h3>
          <p className="meta">相对当前日记日期范围，已缓存历史天气的比例。</p>
          <ul className="completeness-list">
            <li>天气：{Math.round(completeness.weather * 100)}%</li>
          </ul>
          <p className="hint">在上方保存常驻城市后，运行分析时会自动拉取 Open-Meteo 天气。</p>
        </div>
      )}

      {feedbackSummary && feedbackSummary.total > 0 && (
        <div className="card">
          <h3>报告反馈汇总</h3>
          <p className="meta">
            共 {feedbackSummary.total} 条 · 👍 {feedbackSummary.up} · 👎 {feedbackSummary.down}
          </p>
          <ul className="completeness-list">
            {Object.entries(feedbackSummary.byRun).map(([runId, counts]) => (
              <li key={runId}>
                {runId}：👍 {counts.up} · 👎 {counts.down}
              </li>
            ))}
          </ul>
          <p className="hint">反馈保存在 data/feedback/，删除全部本地数据时会一并清除。</p>
          <button type="button" className="secondary" disabled={exportingFeedback} onClick={handleExportFeedback}>
            {exportingFeedback ? '导出中…' : '导出反馈 JSON'}
          </button>
        </div>
      )}

      <div className="card">
        <h3>日记原文</h3>
        {inventory && inventory.entries > 0 && (
          <p className="meta">当前本地共有 {inventory.entries} 篇日记原文。</p>
        )}
        <p className="hint">
          仅删除日记原文文件（data/entries/）。勾选「保留脱敏分析」时，会抹除分析产物中的原文片段与 units/morphs 等可还原字段，保留情绪曲线、主题、锚点结论等聚合结果。
        </p>
        <label className="field checkbox-field">
          <input
            type="checkbox"
            checked={preserveAnonymizedAnalysis}
            onChange={(e) => setPreserveAnonymizedAnalysis(e.target.checked)}
          />
          保留脱敏后的分析结果
        </label>
        <label className="field">
          输入「确认删除日记」以启用按钮
          <input
            type="text"
            value={deleteEntriesConfirm}
            onChange={(e) => setDeleteEntriesConfirm(e.target.value)}
            placeholder="确认删除日记"
            autoComplete="off"
          />
        </label>
        <button
          type="button"
          className="secondary"
          disabled={deletingEntries || deleteEntriesConfirm !== '确认删除日记' || !inventory?.entries}
          onClick={handleDeleteEntries}
        >
          {deletingEntries ? '删除中…' : '删除全部日记原文'}
        </button>
        {deleteEntriesResult && <p className="success-inline">{deleteEntriesResult}</p>}
      </div>

      <div className="card danger-zone">
        <h3>数据管理</h3>
        {inventory && (
          <p className="meta">
            当前：日记 {inventory.entries} 篇 · 分析 {inventory.analysisRuns} 次 · 语境文件 {inventory.contextFiles}{' '}
            个
          </p>
        )}
        <p className="hint">
          一键删除将清除本机全部日记、分析结果、语境导入与叙事编辑，不可恢复。城市设置会保留。
        </p>
        <label className="field">
          输入「确认删除」以启用按钮
          <input
            type="text"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder="确认删除"
            autoComplete="off"
          />
        </label>
        <button
          type="button"
          className="danger"
          disabled={deleting || deleteConfirm !== '确认删除'}
          onClick={handleDeleteAll}
        >
          {deleting ? '删除中…' : '删除全部本地数据'}
        </button>
        {deleteResult && <p className="success-inline">{deleteResult}</p>}
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
