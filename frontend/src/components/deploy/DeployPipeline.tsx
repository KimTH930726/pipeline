import type { StageInfo } from '../../types/deploy';
import { CheckCircle2, XCircle, Loader2, Circle } from 'lucide-react';

interface Props {
  stages: StageInfo[];
  buildStatus: string | null;
}

const stageIcon = (status: StageInfo['status']) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={20} className="text-green-500" />;
    case 'failed':
      return <XCircle size={20} className="text-red-500" />;
    case 'started':
      return <Loader2 size={20} className="text-blue-500 animate-spin" />;
    default:
      return <Circle size={20} className="text-gray-300" />;
  }
};

const stageStyle = (status: StageInfo['status']) => {
  switch (status) {
    case 'completed':
      return 'border-green-200 bg-green-50';
    case 'failed':
      return 'border-red-200 bg-red-50';
    case 'started':
      return 'border-blue-300 bg-blue-50 ring-2 ring-blue-100';
    default:
      return 'border-gray-200 bg-gray-50';
  }
};

const stageLabel = (status: StageInfo['status']) => {
  switch (status) {
    case 'completed':
      return <span className="text-xs text-green-600 font-medium">완료</span>;
    case 'failed':
      return <span className="text-xs text-red-600 font-medium">실패</span>;
    case 'started':
      return <span className="text-xs text-blue-600 font-medium">진행 중...</span>;
    default:
      return <span className="text-xs text-gray-400">대기</span>;
  }
};

const connectorColor = (status: StageInfo['status']) => {
  switch (status) {
    case 'completed':
      return 'bg-green-400';
    case 'failed':
      return 'bg-red-400';
    default:
      return 'bg-gray-200';
  }
};

export default function DeployPipeline({ stages, buildStatus }: Props) {
  if (!buildStatus) return null;

  return (
    <div className="flex items-center gap-0 w-full">
      {stages.map((stage, i) => (
        <div key={stage.key} className="flex items-center flex-1">
          <div className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border w-full transition-all duration-300 ${stageStyle(stage.status)}`}>
            {stageIcon(stage.status)}
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">{stage.label}</p>
              {stageLabel(stage.status)}
            </div>
          </div>
          {i < stages.length - 1 && (
            <div className={`w-8 h-0.5 flex-shrink-0 transition-colors duration-300 ${connectorColor(stage.status)}`} />
          )}
        </div>
      ))}
    </div>
  );
}
