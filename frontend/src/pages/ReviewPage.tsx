import { useState } from 'react';
import Markdown from 'react-markdown';
import { Shield, Search, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import Header from '../components/layout/Header';
import BranchSelector from '../components/git/BranchSelector';
import ChangedFileList from '../components/git/ChangedFileList';
import DiffViewer from '../components/git/DiffViewer';
import ImpactAnalysisPanel from '../components/git/ImpactAnalysisPanel';
import { fetchChangedFiles, fetchDiff, analyzeImpact, reviewCode, fetchCommitMessages } from '../api/gitApi';
import type { CodeReviewResponse } from '../api/gitApi';
import { getReviewStatus, approveReview, rejectReview, type ReviewResponse } from '../api/reviewApi';
import type { FileChange, ImpactAnalysisResponse } from '../types/git';

export default function ReviewPage() {
  const [branch, setBranch] = useState('');
  const [files, setFiles] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [diffText, setDiffText] = useState('');

  const [analysis, setAnalysis] = useState<ImpactAnalysisResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [codeReview, setCodeReview] = useState<CodeReviewResponse | null>(null);
  const [reviewing, setReviewing] = useState(false);

  const [commitMessages, setCommitMessages] = useState<string[]>([]);

  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [comment, setComment] = useState('');
  const [reviewLoading, setReviewLoading] = useState(false);

  const handleBranchSelect = async (b: string) => {
    setBranch(b);
    setSelectedFile('');
    setDiffText('');
    setAnalysis(null);
    setCodeReview(null);
    setReview(null);
    setComment('');
    setCommitMessages([]);
    if (!b) { setFiles([]); return; }
    try {
      const [changed, reviewStatus, commits] = await Promise.all([
        fetchChangedFiles(b),
        getReviewStatus(b).catch(() => null),
        fetchCommitMessages(b).catch(() => ({ commits: [] })),
      ]);
      setFiles(changed);
      setReview(reviewStatus);
      setCommitMessages(commits.commits || []);
    } catch {
      setFiles([]);
    }
  };

  const handleFileSelect = async (path: string) => {
    setSelectedFile(path);
    try {
      const diff = await fetchDiff(branch, path);
      setDiffText(diff.diff_text);
    } catch {
      setDiffText('');
    }
  };

  const handleAnalyze = async () => {
    if (!branch) return;
    setAnalyzing(true);
    try {
      const result = await analyzeImpact(branch);
      setAnalysis(result);
    } catch {
      setAnalysis(null);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleCodeReview = async () => {
    if (!branch) return;
    setReviewing(true);
    try {
      const result = await reviewCode(branch);
      setCodeReview(result);
    } catch {
      setCodeReview(null);
    } finally {
      setReviewing(false);
    }
  };

  const handleApprove = async () => {
    if (!branch) return;
    setReviewLoading(true);
    try {
      const result = await approveReview(branch, comment || undefined);
      setReview(result);
      setComment('');
    } catch { /* ignore */ }
    finally { setReviewLoading(false); }
  };

  const handleReject = async () => {
    if (!branch) return;
    setReviewLoading(true);
    try {
      const result = await rejectReview(branch, comment || undefined);
      setReview(result);
      setComment('');
    } catch { /* ignore */ }
    finally { setReviewLoading(false); }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      APPROVED: 'bg-green-100 text-green-700',
      REJECTED: 'bg-red-100 text-red-700',
      PENDING: 'bg-yellow-100 text-yellow-700',
    };
    const labelMap: Record<string, string> = {
      APPROVED: '승인됨',
      REJECTED: '반려됨',
      PENDING: '대기 중',
    };
    return (
      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${map[status] || 'bg-gray-100 text-gray-600'}`}>
        {labelMap[status] || status}
      </span>
    );
  };

  const severityIcon = (severity: string) => {
    if (severity === 'critical') return <AlertTriangle size={14} className="text-red-500" />;
    if (severity === 'warning') return <Info size={14} className="text-yellow-500" />;
    return <CheckCircle size={14} className="text-blue-500" />;
  };

  const severityStyle = (severity: string) => {
    if (severity === 'critical') return 'border-red-200 bg-red-50';
    if (severity === 'warning') return 'border-yellow-200 bg-yellow-50';
    return 'border-blue-200 bg-blue-50';
  };

  const qualityBadge = (q: string) => {
    const map: Record<string, { color: string; label: string }> = {
      good: { color: 'bg-green-100 text-green-700', label: '양호' },
      needs_improvement: { color: 'bg-yellow-100 text-yellow-700', label: '개선 필요' },
      poor: { color: 'bg-red-100 text-red-700', label: '문제 있음' },
    };
    const c = map[q] || map.needs_improvement;
    return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.color}`}>{c.label}</span>;
  };

  return (
    <div>
      <Header title="코드 리뷰" subtitle="브랜치별 변경사항 확인 및 AI 분석 / 승인 처리" />

      <div className="flex items-center gap-3 mb-6">
        <BranchSelector selected={branch} onSelect={handleBranchSelect} excludeMain />
        {branch && (
          <>
            <button
              onClick={handleAnalyze}
              disabled={analyzing || files.length === 0}
              className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
              title={files.length === 0 ? '변경된 파일이 없습니다' : ''}
            >
              <Shield size={14} />
              {analyzing ? '분석 중...' : 'AI 영향도 분석'}
            </button>
            <button
              onClick={handleCodeReview}
              disabled={reviewing || files.length === 0}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              <Search size={14} />
              {reviewing ? '리뷰 중...' : 'AI 코드 리뷰'}
            </button>
          </>
        )}
        {review && statusBadge(review.status)}
      </div>

      {/* AI 영향도 분석 결과 */}
      {analysis && (
        <div className="mb-6">
          <ImpactAnalysisPanel analysis={analysis} loading={analyzing} />
        </div>
      )}

      {/* AI 코드 리뷰 결과 */}
      {codeReview && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Search size={18} className="text-indigo-600" />
              <h3 className="font-semibold text-gray-800">AI 코드 리뷰</h3>
              {qualityBadge(codeReview.overall_quality)}
            </div>
            <span className="text-xs text-gray-400">{codeReview.comments.length}건의 코멘트</span>
          </div>

          <div className="text-sm text-gray-700 mb-4 prose prose-sm max-w-none">
            <Markdown>{codeReview.summary}</Markdown>
          </div>

          <div className="space-y-3">
            {codeReview.comments.map((c, i) => (
              <div key={i} className={`border rounded-lg p-3 ${severityStyle(c.severity)}`}>
                <div className="flex items-center gap-2 mb-1">
                  {severityIcon(c.severity)}
                  <span className="text-xs font-mono text-gray-600">{c.file_path}{c.line ? `:${c.line}` : ''}</span>
                  <span className="px-1.5 py-0.5 bg-white/70 rounded text-xs text-gray-500">{c.category}</span>
                </div>
                <div className="text-sm prose prose-sm max-w-none">
                  <Markdown>{c.message}</Markdown>
                </div>
                {c.suggested_code && (
                  <pre className="mt-2 text-xs bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{c.suggested_code}</pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 승인/반려 패널 */}
      {branch && files.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">리뷰 결정</h3>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">코멘트 (선택)</label>
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="리뷰 의견을 남겨주세요"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <button
              onClick={handleApprove}
              disabled={reviewLoading || review?.status === 'APPROVED'}
              className="px-5 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {review?.status === 'APPROVED' ? '승인됨' : reviewLoading ? '처리 중...' : '승인'}
            </button>
            <button
              onClick={handleReject}
              disabled={reviewLoading || review?.status === 'REJECTED'}
              className="px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
            >
              {review?.status === 'REJECTED' ? '반려됨' : '반려'}
            </button>
          </div>
          {review?.comment && (
            <p className="mt-2 text-sm text-gray-500">
              마지막 코멘트: {review.comment}
            </p>
          )}
        </div>
      )}

      {/* 커밋 메시지 */}
      {commitMessages.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">커밋 내역 ({commitMessages.length}건)</h3>
          <div className="space-y-1">
            {commitMessages.map((msg, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 mt-0.5">&bull;</span>
                <span className="text-gray-700 font-mono text-xs">{msg}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-1 bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="p-3 bg-gray-50 border-b text-sm font-semibold text-gray-600">
            변경 파일 ({files.length})
          </div>
          <ChangedFileList files={files} selectedPath={selectedFile} onSelect={handleFileSelect} />
        </div>
        <div className="col-span-2">
          <DiffViewer diffText={diffText} filePath={selectedFile} />
        </div>
      </div>
    </div>
  );
}
