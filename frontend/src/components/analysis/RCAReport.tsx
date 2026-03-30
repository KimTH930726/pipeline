import { useState } from 'react';
import Markdown from 'react-markdown';
import { AlertTriangle, FileCode, Wrench, Copy, Check, Bot } from 'lucide-react';
import type { RCAReport as RCAReportType } from '../../types/deploy';

interface Props {
  report: RCAReportType;
}

export default function RCAReport({ report }: Props) {
  const confidencePercent = Math.round(report.confidence_score * 100);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(report.ai_fix_prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-red-200 bg-red-50 rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="text-red-500" size={20} />
        <h3 className="font-bold text-red-700">AI 실패 원인 분석</h3>
        <span className="ml-auto text-xs text-gray-500">
          신뢰도: {confidencePercent}%
        </span>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-red-600 mb-1 flex items-center gap-1">
          <AlertTriangle size={12} /> 원인 (Root Cause)
        </h4>
        <div className="text-sm text-gray-800 prose prose-sm max-w-none">
          <Markdown>{report.root_cause}</Markdown>
        </div>
      </div>

      {report.affected_files.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-red-600 mb-1 flex items-center gap-1">
            <FileCode size={12} /> 영향 파일
          </h4>
          <div className="flex flex-wrap gap-1">
            {report.affected_files.map((f) => (
              <span key={f} className="text-xs px-2 py-0.5 bg-white rounded border border-red-200 font-mono">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <h4 className="text-xs font-semibold text-red-600 mb-1 flex items-center gap-1">
          <Wrench size={12} /> 수정 가이드
        </h4>
        <div className="text-sm text-gray-800 prose prose-sm max-w-none">
          <Markdown>{report.suggested_fix}</Markdown>
        </div>
      </div>

      {report.ai_fix_prompt && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-xs font-semibold text-red-600 flex items-center gap-1">
              <Bot size={12} /> AI 수정 요청 프롬프트
            </h4>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-200 hover:bg-white transition-colors"
            >
              {copied ? <><Check size={10} className="text-green-600" /> 복사됨</> : <><Copy size={10} /> 복사</>}
            </button>
          </div>
          <div className="text-xs text-gray-700 bg-white border border-red-200 rounded p-3 prose prose-xs max-w-none">
            <Markdown>{report.ai_fix_prompt}</Markdown>
          </div>
        </div>
      )}

      <div className="w-full bg-gray-200 rounded-full h-1.5">
        <div
          className="bg-red-500 h-1.5 rounded-full transition-all"
          style={{ width: `${confidencePercent}%` }}
        />
      </div>
    </div>
  );
}
