import type { EmotionPoint } from '../../types/analysis';

interface Props {
  series: EmotionPoint[];
  width?: number;
  height?: number;
}

export default function EmotionTimelineChart({ series, width = 520, height = 120 }: Props) {
  if (series.length < 2) return null;

  const sorted = [...series].sort((a, b) => a.date.localeCompare(b.date));
  const pad = { left: 28, right: 8, top: 12, bottom: 22 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const minScore = 1;
  const maxScore = 10;

  const points = sorted.map((p, i) => {
    const x = pad.left + (i / (sorted.length - 1)) * innerW;
    const y = pad.top + innerH - ((p.score - minScore) / (maxScore - minScore)) * innerH;
    return { x, y, ...p };
  });

  const polyline = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  const best = points.reduce((a, b) => (a.score >= b.score ? a : b));
  const worst = points.reduce((a, b) => (a.score <= b.score ? a : b));

  return (
    <div className="emotion-timeline-chart">
      <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="emotion-timeline-svg">
        {[2, 5, 8].map((tick) => {
          const y = pad.top + innerH - ((tick - minScore) / (maxScore - minScore)) * innerH;
          return (
            <g key={tick}>
              <line
                x1={pad.left}
                y1={y}
                x2={width - pad.right}
                y2={y}
                stroke="currentColor"
                strokeOpacity={0.08}
              />
              <text x={4} y={y + 4} className="chart-axis-label">{tick}</text>
            </g>
          );
        })}
        <polyline
          points={polyline}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((p) => (
          <circle key={p.date} cx={p.x} cy={p.y} r={2.5} fill="currentColor" />
        ))}
        <circle cx={best.x} cy={best.y} r={4} className="chart-marker-best" />
        <circle cx={worst.x} cy={worst.y} r={4} className="chart-marker-worst" />
      </svg>
      <p className="meta chart-legend">
        最高 {best.score.toFixed(1)}（{best.date}）· 最低 {worst.score.toFixed(1)}（{worst.date}）
      </p>
    </div>
  );
}
