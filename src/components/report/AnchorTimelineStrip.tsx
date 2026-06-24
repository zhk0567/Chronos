import type { AnchorCard } from '../../types/analysis';
import { anchorTypeLabel } from '../../utils/anchorLabels';

interface Props {
  anchors: AnchorCard[];
  startDate: string;
  endDate: string;
  onSelectAnchor?: () => void;
}

export default function AnchorTimelineStrip({ anchors, startDate, endDate, onSelectAnchor }: Props) {
  if (anchors.length === 0) return null;

  const start = new Date(startDate).getTime();
  const end = new Date(endDate).getTime();
  const span = Math.max(end - start, 1);

  const sorted = [...anchors].sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="anchor-timeline-strip">
      <p className="meta">锚点时间分布（{sorted.length} 个）</p>
      <div className="anchor-timeline-track">
        {sorted.map((a) => {
          const t = new Date(a.date).getTime();
          const pct = ((t - start) / span) * 100;
          return (
            <button
              key={a.id}
              type="button"
              className="anchor-timeline-dot"
              style={{ left: `${Math.min(98, Math.max(0, pct))}%` }}
              title={`${a.date} ${a.title}`}
              onClick={onSelectAnchor}
            >
              <span className="anchor-dot-label">{anchorTypeLabel(a.emergenceType)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
