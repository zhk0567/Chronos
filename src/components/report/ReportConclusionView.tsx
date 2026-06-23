import type { ReportConclusion } from '../../types/analysis';
import EvidencePanel from './EvidencePanel';

interface Props {
  conclusion: ReportConclusion;
}

export default function ReportConclusionView({ conclusion }: Props) {
  return (
    <div className="conclusion-card reading">
      <p className="statement">{conclusion.statement}</p>
      <p className="confidence">置信度 {Math.round(conclusion.confidence * 100)}%</p>
      {conclusion.limitation && <p className="limitation">{conclusion.limitation}</p>}
      <EvidencePanel evidence={conclusion.evidence} />
    </div>
  );
}
