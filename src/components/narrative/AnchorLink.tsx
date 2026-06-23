import { Link } from 'react-router-dom';

interface AnchorLinkProps {
  runId: string;
  anchorId: string;
  label?: string;
}

export default function AnchorLink({ runId, anchorId, label }: AnchorLinkProps) {
  return (
    <Link to="/story" state={{ runId, anchorId }} className="anchor-link">
      {label ?? `锚点 ${anchorId}`}
    </Link>
  );
}
