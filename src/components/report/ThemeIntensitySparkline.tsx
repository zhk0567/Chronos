interface Props {
  curve: { date: string; intensity: number }[];
  width?: number;
  height?: number;
}

export default function ThemeIntensitySparkline({ curve, width = 120, height = 32 }: Props) {
  if (curve.length < 2) return null;
  const values = curve.map((p) => p.intensity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = 2;
  const points = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (width - pad * 2);
      const y = pad + (height - pad * 2) - ((v - min) / range) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg className="theme-intensity-sparkline" viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
