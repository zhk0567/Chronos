import type { InsightReport, ReportSection } from '../../types/analysis';
import ReportConclusionView from './ReportConclusionView';
import WeatherMoodCompare from './WeatherMoodCompare';
import WeatherScatterChart from './WeatherScatterChart';
import ThemeIntensitySparkline from './ThemeIntensitySparkline';

interface Props {
  section: ReportSection;
  report?: InsightReport | null;
}

export default function ReportSectionView({ section, report }: Props) {
  const rainInsight = report?.weatherInsights?.find(
    (w) => w.type === 'rain_compare' && w.chartData?.labels?.length
  );
  const bandInsight = report?.weatherInsights?.find(
    (w) => w.type === 'temp_band' && w.chartData?.labels?.length
  );
  const weatherChart = rainInsight ?? bandInsight;

  return (
    <div className="report-section">
      <h3>{section.title}</h3>

      {section.id === 'environment' && weatherChart?.chartData && (
        <WeatherMoodCompare
          labels={weatherChart.chartData.labels as string[]}
          values={weatherChart.chartData.values as number[]}
        />
      )}
      {section.id === 'environment' && report?.dailyContexts && report.emotionSeries && (
        <WeatherScatterChart contexts={report.dailyContexts} emotionSeries={report.emotionSeries} />
      )}

      {section.id === 'stability' && report && report.emotionSeries.length >= 2 && (
        <p className="hint">情绪时间线见上方「分析总览」。</p>
      )}

      {section.id === 'themes' && report?.themes && report.themes.length > 0 && (
        <ul className="theme-curve-list meta">
          {report.themes.slice(0, 8).map((t) => (
            <li key={t.theme}>
              {t.theme}
              {t.intensityCurve.length >= 2 && (
                <ThemeIntensitySparkline curve={t.intensityCurve} />
              )}
            </li>
          ))}
        </ul>
      )}

      {section.conclusions.map((c) => (
        <ReportConclusionView key={c.id} conclusion={c} />
      ))}
    </div>
  );
}
