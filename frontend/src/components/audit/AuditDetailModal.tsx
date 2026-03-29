import { X } from 'lucide-react';
import type { AuditEntry } from '../../types/audit';

interface Props {
  entry: AuditEntry;
  onClose: () => void;
}

export default function AuditDetailModal({ entry, onClose }: Props) {
  const time = new Date(entry.created_at).toLocaleString('ko-KR');

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-bold text-lg">감사 로그 상세</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">이벤트</span>
              <p className="font-semibold">{entry.event_type}</p>
            </div>
            <div>
              <span className="text-gray-500">브랜치</span>
              <p className="font-mono">{entry.branch}</p>
            </div>
            <div>
              <span className="text-gray-500">커밋</span>
              <p className="font-mono">{entry.commit_sha || '-'}</p>
            </div>
            <div>
              <span className="text-gray-500">시간</span>
              <p>{time}</p>
            </div>
          </div>

          {entry.ai_report && (
            <div>
              <h4 className="text-sm font-semibold text-purple-600 mb-2">AI 분석 리포트</h4>
              <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto font-mono">
                {JSON.stringify(entry.ai_report, null, 2)}
              </pre>
            </div>
          )}

          {entry.metadata_ && (
            <div>
              <h4 className="text-sm font-semibold text-gray-600 mb-2">메타데이터</h4>
              <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto font-mono">
                {JSON.stringify(entry.metadata_, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
