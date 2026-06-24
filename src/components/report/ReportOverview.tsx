import type { InsightReport } from '../../types/analysis';
import EmotionTimelineChart from './EmotionTimelineChart';
import AnchorTimelineStrip from './AnchorTimelineStrip';
import WeatherMoodCompare from './WeatherMoodCompare';
import WeatherScatterChart from './WeatherScatterChart';

interface Props {
  report: InsightReport;
  onOpenAnchors: () => void;
}

export default function ReportOverview({ report, onOpenAnchors }: Props) {
  const rainInsight = report.weatherInsights?.find(
    (w) => w.type === 'rain_compare' && w.chartData?.labels?.length
  );
  const bandInsight = report.weatherInsights?.find(
    (w) => w.type === 'temp_band' && w.chartData?.labels?.length
  );
  const chartInsight = rainInsight ?? bandInsight;

  return (
    <div className="card report-overview">
      <h3>分析总览</h3>
      {report.executiveSummary && report.executiveSummary.length > 0 && (
        <ul className="executive-summary">
          {report.executiveSummary.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}

      {report.emotionSeries.length >= 2 && (
        <EmotionTimelineChart series={report.emotionSeries} />
      )}

      <AnchorTimelineStrip
        anchors={report.anchors}
        startDate={report.dateRange.start}
        endDate={report.dateRange.end}
        onSelectAnchor={onOpenAnchors}
      />

      {chartInsight?.chartData && (
        <WeatherMoodCompare
          labels={chartInsight.chartData.labels as string[]}
          values={chartInsight.chartData.values as number[]}
        />
      )}

      {report.dailyContexts && report.dailyContexts.length > 0 && (
        <WeatherScatterChart
          contexts={report.dailyContexts}
          emotionSeries={report.emotionSeries}
        />
      )}
    </div>
  );
}
