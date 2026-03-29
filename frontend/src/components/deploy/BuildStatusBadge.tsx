import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';

interface Props {
  status: string | null;
}

const config: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  PENDING: { icon: Clock, color: 'text-gray-500 bg-gray-100', label: '대기' },
  BUILDING: { icon: Loader2, color: 'text-blue-600 bg-blue-100', label: '빌드 중' },
  SUCCESS: { icon: CheckCircle, color: 'text-green-600 bg-green-100', label: '성공' },
  FAILED: { icon: XCircle, color: 'text-red-600 bg-red-100', label: '실패' },
};

export default function BuildStatusBadge({ status }: Props) {
  if (!status) return null;

  const c = config[status] || config.PENDING;
  const Icon = c.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium ${c.color}`}>
      <Icon size={14} className={status === 'BUILDING' ? 'animate-spin' : ''} />
      {c.label}
    </span>
  );
}
