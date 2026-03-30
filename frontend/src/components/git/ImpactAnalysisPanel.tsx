import Markdown from 'react-markdown';
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';
import type { ImpactAnalysisResponse } from '../../types/git';

interface Props {
  analysis: ImpactAnalysisResponse | null;
  loading?: boolean;
}

const riskConfig: Record<string, { color: string; icon: typeof Info; label: string }> = {
  LOW: { color: 'text-green-600 bg-green-50 border-green-200', icon: CheckCircle, label: '낮음' },
  MEDIUM: { color: 'text-yellow-600 bg-yellow-50 border-yellow-200', icon: Info, label: '중간' },
  HIGH: { color: 'text-orange-600 bg-orange-50 border-orange-200', icon: AlertTriangle, label: '높음' },
  CRITICAL: { color: 'text-red-600 bg-red-50 border-red-200', icon: XCircle, label: '위험' },
};

export default function ImpactAnalysisPanel({ analysis, loading }: Props) {
  if (loading) {
    return (
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          AI가 영향도를 분석 중입니다...
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const config = riskConfig[analysis.risk_level] || riskConfig.MEDIUM;
  const Icon = config.icon;

  return (
    <div className={`border rounded-lg p-4 ${config.color}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={20} />
        <span className="font-semibold">영향도: {config.label}</span>
      </div>
      <div className="text-sm mb-3 prose prose-sm max-w-none">
        <Markdown>{analysis.summary}</Markdown>
      </div>
      <div className="mb-3">
        <h4 className="text-xs font-semibold mb-1 opacity-70">영향 서비스</h4>
        <div className="flex flex-wrap gap-1">
          {analysis.affected_services.map((s) => (
            <span key={s} className="text-xs px-2 py-0.5 bg-white/50 rounded">{s}</span>
          ))}
        </div>
      </div>
      <div>
        <h4 className="text-xs font-semibold mb-1 opacity-70">권장사항</h4>
        <div className="text-xs space-y-1 prose prose-xs max-w-none">
          {analysis.recommendations.map((r, i) => (
            <Markdown key={i}>{r}</Markdown>
          ))}
        </div>
      </div>
    </div>
  );
}
