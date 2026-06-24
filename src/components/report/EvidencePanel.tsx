import type { Evidence } from '../../types/analysis';

const SOURCE_LABELS: Record<string, string> = {
  explicit: '原文',
  inferred: '推断',
};

interface Props {
  evidence: Evidence[];
}

export default function EvidencePanel({ evidence }: Props) {
  if (evidence.length === 0) return null;

  return (
    <details className="evidence-panel">
      <summary>证据链 ({evidence.length})</summary>
      <ul>
        {evidence.map((e, i) => (
          <li key={i}>
            <span className="ev-date">{e.date}</span>
            <span className="ev-source">[{SOURCE_LABELS[e.source] ?? e.source}]</span>
            <span className="ev-text">{e.text}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
