import { useState } from 'react';
import Header from '../components/layout/Header';
import BranchSelector from '../components/git/BranchSelector';
import ChangedFileList from '../components/git/ChangedFileList';
import DiffViewer from '../components/git/DiffViewer';
import ImpactAnalysisPanel from '../components/git/ImpactAnalysisPanel';
import { fetchChangedFiles, fetchDiff, analyzeImpact } from '../api/gitApi';
import type { FileChange, ImpactAnalysisResponse } from '../types/git';

export default function ReviewPage() {
  const [branch, setBranch] = useState('');
  const [files, setFiles] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [diffText, setDiffText] = useState('');
  const [analysis, setAnalysis] = useState<ImpactAnalysisResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const handleBranchSelect = async (b: string) => {
    setBranch(b);
    setSelectedFile('');
    setDiffText('');
    setAnalysis(null);
    if (!b) return;
    try {
      const changed = await fetchChangedFiles(b);
      setFiles(changed);
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

  return (
    <div>
      <Header title="코드 리뷰" subtitle="브랜치별 변경사항 확인 및 AI 영향도 분석" />

      <div className="flex items-center gap-4 mb-6">
        <BranchSelector selected={branch} onSelect={handleBranchSelect} />
        {branch && (
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
          >
            {analyzing ? '분석 중...' : 'AI 영향도 분석'}
          </button>
        )}
      </div>

      {analysis && (
        <div className="mb-6">
          <ImpactAnalysisPanel analysis={analysis} loading={analyzing} />
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
