import { useCallback, useEffect, useState } from 'react';
import type { ContextCompleteness, UserSettings, WeatherTestResult } from '../types/analysis';

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>({
    residentCity: '',
    latitude: null,
    longitude: null,
    timezone: 'Asia/Shanghai',
  });
  const [completeness, setCompleteness] = useState<ContextCompleteness | null>(null);
  const [cityInput, setCityInput] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [testing, setTesting] = useState(false);
  const [weatherTest, setWeatherTest] = useState<WeatherTestResult | null>(null);

  const refresh = useCallback(async () => {
    const s = await window.chronosAPI.getSettings();
    setSettings(s);
    setCityInput(s.residentCity);
    setCompleteness(await window.chronosAPI.getContextCompleteness());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSave = async () => {
    setError('');
    setWeatherTest(null);
    try {
      const s = await window.chronosAPI.saveSettings({ residentCity: cityInput.trim() });
      setSettings(s);
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

      {completeness && (
        <div className="card">
          <h3>语境数据完整度</h3>
          <ul className="completeness-list">
            <li>天气：{Math.round(completeness.weather * 100)}%</li>
            <li>可穿戴：{Math.round(completeness.wearable * 100)}%</li>
            <li>数字行为：{Math.round(completeness.digital * 100)}%</li>
            <li>位置：{Math.round(completeness.location * 100)}%</li>
            <li>时间节律：{Math.round(completeness.rhythm * 100)}%</li>
          </ul>
          <p className="hint">完整度在分析时更新；可穿戴/数字/位置数据请在「数据源」页导入</p>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
