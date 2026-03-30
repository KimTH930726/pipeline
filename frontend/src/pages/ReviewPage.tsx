import { useState } from 'react';
import Header from '../components/layout/Header';
import BranchSelector from '../components/git/BranchSelector';
import ChangedFileList from '../components/git/ChangedFileList';
import DiffViewer from '../components/git/DiffViewer';
import ImpactAnalysisPanel from '../components/git/ImpactAnalysisPanel';
import { fetchChangedFiles, fetchDiff, analyzeImpact } from '../api/gitApi';
import { getReviewStatus, approveReview, rejectReview, type ReviewResponse } from '../api/reviewApi';
import type { FileChange, ImpactAnalysisResponse } from '../types/git';

export default function ReviewPage() {
  const [branch, setBranch] = useState('');
  const [files, setFiles] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [diffText, setDiffText] = useState('');
  const [analysis, setAnalysis] = useState<ImpactAnalysisResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [comment, setComment] = useState('');
  const [reviewLoading, setReviewLoading] = useState(false);

  const handleBranchSelect = async (b: string) => {
    setBranch(b);
    setSelectedFile('');
    setDiffText('');
    setAnalysis(null);
    setReview(null);
    setComment('');
    if (!b) { setFiles([]); return; }
    try {
      const [changed, reviewStatus] = await Promise.all([
        fetchChangedFiles(b),
        getReviewStatus(b).catch(() => null),
      ]);
      setFiles(changed);
      setReview(reviewStatus);
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

  return (
    <div>
      <Header title="코드 리뷰" subtitle="브랜치별 변경사항 확인 및 승인/반려 처리" />

      <div className="flex items-center gap-4 mb-6">
        <BranchSelector selected={branch} onSelect={handleBranchSelect} />
        {branch && (
          <button
            onClick={handleAnalyze}
            disabled={analyzing || files.length === 0}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
            title={files.length === 0 ? '변경된 파일이 없습니다' : ''}
          >
            {analyzing ? '분석 중...' : 'AI 영향도 분석'}
          </button>
        )}
        {review && statusBadge(review.status)}
      </div>

      {analysis && (
        <div className="mb-6">
          <ImpactAnalysisPanel analysis={analysis} loading={analyzing} />
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
              disabled={reviewLoading}
              className="px-5 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {reviewLoading ? '처리 중...' : '승인'}
            </button>
            <button
              onClick={handleReject}
              disabled={reviewLoading}
              className="px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
            >
              반려
            </button>
          </div>
          {review?.comment && (
            <p className="mt-2 text-sm text-gray-500">
              마지막 코멘트: {review.comment}
            </p>
          )}
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
