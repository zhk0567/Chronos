import type { DailyContext, EmotionPoint } from '../../types/analysis';

interface Props {
  contexts: DailyContext[];
  emotionSeries: EmotionPoint[];
  width?: number;
  height?: number;
}

export default function WeatherScatterChart({
  contexts,
  emotionSeries,
  width = 280,
  height = 140,
}: Props) {
  const emotionByDate = new Map(emotionSeries.map((p) => [p.date, p.score]));
  const points: { temp: number; score: number; date: string }[] = [];

  for (const ctx of contexts) {
    if (!ctx.weather?.temp) continue;
    const score = emotionByDate.get(ctx.date);
    if (score == null) continue;
    points.push({ temp: ctx.weather.temp, score, date: ctx.date });
  }

  if (points.length < 4) return null;

  const temps = points.map((p) => p.temp);
  const scores = points.map((p) => p.score);
  const minT = Math.min(...temps);
  const maxT = Math.max(...temps);
  const pad = 12;
  const spanT = maxT - minT || 1;

  return (
    <div className="weather-scatter-chart">
      <p className="meta">气温与情绪（{points.length} 天）</p>
      <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
        {points.map((p) => {
          const x = pad + ((p.temp - minT) / spanT) * (width - pad * 2);
          const y = pad + (height - pad * 2) - ((p.score - 1) / 9) * (height - pad * 2);
          return <circle key={p.date} cx={x} cy={y} r={3} fill="currentColor" opacity={0.75} />;
        })}
      </svg>
      <p className="meta">横轴：气温 · 纵轴：情绪 1–10</p>
    </div>
  );
}
