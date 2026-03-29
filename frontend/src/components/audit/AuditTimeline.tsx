import { GitBranch, Play, AlertTriangle, RotateCcw, Brain } from 'lucide-react';
import type { AuditEntry } from '../../types/audit';

interface Props {
  entries: AuditEntry[];
  onSelect?: (entry: AuditEntry) => void;
}

const eventConfig: Record<string, { icon: typeof Play; color: string; label: string }> = {
  DEPLOY: { icon: Play, color: 'bg-blue-500', label: '배포' },
  FAILURE: { icon: AlertTriangle, color: 'bg-red-500', label: '실패' },
  RCA: { icon: Brain, color: 'bg-purple-500', label: 'AI 분석' },
  ROLLBACK: { icon: RotateCcw, color: 'bg-orange-500', label: '원복' },
};

export default function AuditTimeline({ entries, onSelect }: Props) {
  if (!entries.length) {
    return <p className="text-sm text-gray-400 p-4">감사 로그가 없습니다.</p>;
  }

  return (
    <div className="space-y-0">
      {entries.map((entry) => {
        const config = eventConfig[entry.event_type] || { icon: GitBranch, color: 'bg-gray-500', label: entry.event_type };
        const Icon = config.icon;
        const time = new Date(entry.created_at).toLocaleString('ko-KR');

        return (
          <div
            key={entry.id}
            onClick={() => onSelect?.(entry)}
            className="flex gap-4 p-3 hover:bg-gray-50 cursor-pointer rounded-lg transition-colors"
          >
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full ${config.color} flex items-center justify-center`}>
                <Icon size={14} className="text-white" />
              </div>
              <div className="w-px flex-1 bg-gray-200 mt-1" />
            </div>
            <div className="flex-1 pb-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-gray-800">{config.label}</span>
                <span className="text-xs text-gray-400 font-mono">{entry.branch}</span>
                {entry.commit_sha && (
                  <span className="text-xs text-gray-400 font-mono">{entry.commit_sha.slice(0, 8)}</span>
                )}
              </div>
              <p className="text-xs text-gray-500">{time}</p>
              {entry.ai_report && (
                <p className="text-xs text-purple-600 mt-1">AI 분석 리포트 포함</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
