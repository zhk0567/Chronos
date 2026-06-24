interface Props {
  arc: number[];
  width?: number;
  height?: number;
}

export default function EmotionArcSparkline({ arc, width = 140, height = 36 }: Props) {
  if (arc.length < 2) return null;

  const min = Math.min(...arc);
  const max = Math.max(...arc);
  const range = max - min || 1;
  const pad = 2;

  const points = arc
    .map((value, index) => {
      const x = pad + (index / (arc.length - 1)) * (width - pad * 2);
      const y = pad + (height - pad * 2) - ((value - min) / range) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="emotion-arc-wrap" title={`情绪 ${min.toFixed(1)}–${max.toFixed(1)}`}>
      <span className="meta emotion-arc-label">情绪弧线</span>
      <svg
        className="emotion-arc-sparkline"
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        aria-hidden
      >
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      </svg>
    </div>
  );
}
