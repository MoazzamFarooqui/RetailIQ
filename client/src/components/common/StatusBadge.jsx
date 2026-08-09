import { getStatusBadgeClass } from '../../utils/helpers';

export default function StatusBadge({ status }) {
  if (!status) return null;
  return <span className={getStatusBadgeClass(status)}>{status}</span>;
}


