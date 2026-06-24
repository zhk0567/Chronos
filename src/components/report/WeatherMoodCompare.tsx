interface Props {
  labels: string[];
  values: number[];
}

export default function WeatherMoodCompare({ labels, values }: Props) {
  if (labels.length === 0 || values.length === 0) return null;
  const max = Math.max(...values, 1);

  return (
    <div className="weather-mood-compare">
      {labels.map((label, i) => (
        <div key={label} className="weather-bar-row">
          <span className="weather-bar-label">{label}</span>
          <div className="weather-bar-track">
            <div
              className="weather-bar-fill"
              style={{ width: `${(values[i] / max) * 100}%` }}
            />
          </div>
          <span className="weather-bar-value">{values[i].toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}
