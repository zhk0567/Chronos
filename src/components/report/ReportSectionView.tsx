import type { ReportSection } from '../../types/analysis';
import ReportConclusionView from './ReportConclusionView';

interface Props {
  section: ReportSection;
}

export default function ReportSectionView({ section }: Props) {
  return (
    <div className="report-section">
      <h3>{section.title}</h3>
      {section.conclusions.map((c) => (
        <ReportConclusionView key={c.id} conclusion={c} />
      ))}
    </div>
  );
}
