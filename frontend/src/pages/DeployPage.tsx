import { useState, useEffect, useCallback, useRef } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import Header from '../components/layout/Header';
import BuildStatusBadge from '../components/deploy/BuildStatusBadge';
import BuildLogStream from '../components/deploy/BuildLogStream';
import DeployPipeline from '../components/deploy/DeployPipeline';
import ConflictDiffViewer from '../components/deploy/ConflictDiffViewer';
import ChangedFileList from '../components/git/ChangedFileList';
import DiffViewer from '../components/git/DiffViewer';
import RCAReportComponent from '../components/analysis/RCAReport';
import { triggerDeploy } from '../api/deployApi';
import { listApprovedReviews, type ReviewResponse } from '../api/reviewApi';
import Markdown from 'react-markdown';
import { fetchChangedFiles, fetchDiff, checkConflicts, applyResolution } from '../api/gitApi';
import type { MergeConflictResponse } from '../api/gitApi';
import { useBuildStatus } from '../hooks/useBuildStatus';
import { useDeployStore } from '../store/deployStore';
import type { FileChange } from '../types/git';

export default function DeployPage() {
  const [approvedBranches, setApprovedBranches] = useState<ReviewResponse[]>([]);
  const [selectedBranch, setSelectedBranch] = useState('');
  const [loadingApproved, setLoadingApproved] = useState(true);

  const [changedFiles, setChangedFiles] = useState<FileChange[]>([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [diffText, setDiffText] = useState('');
  const [loadingFiles, setLoadingFiles] = useState(false);

  // 충돌
  const [conflictResult, setConflictResult] = useState<MergeConflictResponse | null>(null);
  const [checkingConflicts, setCheckingConflicts] = useState(false);
  const [applyingResolution, setApplyingResolution] = useState(false);

  const { currentDeployment, buildLog, rcaReport, buildStatus, stages, startPipeline, setDeployment, updateStage } = useDeployStore();
  const pipelineRef = useRef<HTMLDivElement>(null);
  useBuildStatus(currentDeployment?.id ?? null);

  const reload = useCallback(() => {
    listApprovedReviews()
      .then(setApprovedBranches)
      .catch(() => setApprovedBranches([]))
      .finally(() => setLoadingApproved(false));
  }, []);

  useEffect(() => { reload(); }, [reload]);
  useAutoRefresh(reload);

  // 빌드 완료/실패 시 승인 브랜치 목록 갱신
  useEffect(() => {
    if (buildStatus === 'SUCCESS' || buildStatus === 'FAILED') {
      reload();
    }
  }, [buildStatus, reload]);

  const handleBranchSelect = async (branch: string) => {
    setSelectedBranch(branch);
    setChangedFiles([]);
    setSelectedFile('');
    setDiffText('');
    if (!branch) return;
    setLoadingFiles(true);
    try {
      const files = await fetchChangedFiles(branch);
      setChangedFiles(files);
    } catch { setChangedFiles([]); }
    finally { setLoadingFiles(false); }
  };

  const handleFileSelect = async (path: string) => {
    setSelectedFile(path);
    try {
      const diff = await fetchDiff(selectedBranch, path);
      setDiffText(diff.diff_text);
    } catch { setDiffText(''); }
  };

  const handleDeploy = async () => {
    if (!selectedBranch) return;

    // 파이프라인 즉시 표시
    startPipeline();
    setTimeout(() => pipelineRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);

    // Step 1: 충돌 체크
    updateStage('CONFLICT_CHECK', 'started');
    setCheckingConflicts(true);
    setConflictResult(null);
    try {
      const result = await checkConflicts(selectedBranch);
      if (result.has_conflicts) {
        updateStage('CONFLICT_CHECK', 'failed');
        setConflictResult(result);
        setCheckingConflicts(false);
        return;
      }
    } catch {
      updateStage('CONFLICT_CHECK', 'failed');
      setCheckingConflicts(false);
      return;
    }
    updateStage('CONFLICT_CHECK', 'completed');
    setCheckingConflicts(false);

    // Step 2~4: 배포 (이후 단계는 WebSocket으로 업데이트)
    try {
      const deployment = await triggerDeploy(selectedBranch);
      setDeployment(deployment);
    } catch (err) {
      console.error('Deploy failed:', err);
    }
  };

  const handleApplyResolution = async () => {
    if (!selectedBranch || !conflictResult) return;
    setApplyingResolution(true);
    try {
      const resolutions: Record<string, string> = {};
      for (const r of conflictResult.resolutions) {
        resolutions[r.file_path] = r.resolved_content;
      }
      await applyResolution(selectedBranch, resolutions);
      setConflictResult(null);
      // 충돌 해결 완료 → 파이프라인 표시 + 충돌 단계 완료
      startPipeline();
      updateStage('CONFLICT_CHECK', 'completed', '충돌 해결 완료');
      setTimeout(() => pipelineRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      // 배포 실행
      const deployment = await triggerDeploy(selectedBranch);
      setDeployment(deployment);
    } catch (err) {
      console.error('Resolution failed:', err);
    } finally {
      setApplyingResolution(false);
    }
  };

  return (
    <div>
      <Header title="배포" subtitle="승인된 브랜치 선택 → 빌드 → main 머지 → Docker 재기동" />

      {/* 승인된 브랜치 선택 */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">승인된 브랜치</h3>
        {loadingApproved ? (
          <p className="text-sm text-gray-500">로딩 중...</p>
        ) : approvedBranches.length === 0 ? (
          <p className="text-sm text-gray-500">승인된 브랜치가 없습니다. 코드 리뷰에서 먼저 승인해주세요.</p>
        ) : (
          <div className="flex items-center gap-3">
            <select
              value={selectedBranch}
              onChange={(e) => handleBranchSelect(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[250px]"
            >
              <option value="">배포할 브랜치 선택</option>
              {approvedBranches.map((r) => (
                <option key={r.branch} value={r.branch}>
                  {r.branch} (승인: {r.reviewed_at ? new Date(r.reviewed_at).toLocaleDateString('ko-KR') : '-'})
                </option>
              ))}
            </select>
            <button
              onClick={handleDeploy}
              disabled={!selectedBranch || buildStatus === 'BUILDING' || checkingConflicts}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {checkingConflicts ? '충돌 확인 중...' : buildStatus === 'BUILDING' ? '빌드 중...' : '배포 실행'}
            </button>
            {buildStatus && <BuildStatusBadge status={buildStatus} />}
          </div>
        )}
        <p className="mt-2 text-xs text-gray-400">
          빌드 성공 시 자동으로 main에 머지되고, Docker가 재빌드/재기동됩니다.
          배포 성공 시 해당 브랜치의 승인 상태가 초기화되며, 샌드박스가 있으면 자동 삭제됩니다.
        </p>
      </div>

      {/* 배포 대상 변경사항 */}
      {selectedBranch && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            배포 대상 변경사항 ({changedFiles.length}개 파일)
          </h3>
          {loadingFiles ? (
            <p className="text-sm text-gray-500">로딩 중...</p>
          ) : changedFiles.length === 0 ? (
            <p className="text-sm text-gray-500">main 대비 변경된 파일이 없습니다.</p>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-1 border border-gray-200 rounded-lg overflow-hidden max-h-[400px] overflow-y-auto">
                <ChangedFileList files={changedFiles} selectedPath={selectedFile} onSelect={handleFileSelect} />
              </div>
              <div className="col-span-2">
                <DiffViewer diffText={diffText} filePath={selectedFile} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* 머지 충돌 해결 UI */}
      {conflictResult && conflictResult.has_conflicts && (
        <div className="bg-white border border-orange-300 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-orange-500 text-lg">&#9888;</span>
            <h3 className="font-semibold text-orange-700">머지 충돌 감지</h3>
            <span className="text-xs text-gray-500">{conflictResult.conflicting_files.length}개 파일</span>
          </div>
          <div className="text-sm text-gray-700 mb-4 prose prose-sm max-w-none">
            <Markdown>{conflictResult.summary}</Markdown>
          </div>

          <div className="space-y-4 mb-4">
            {conflictResult.resolutions.map((r, i) => (
              <div key={i} className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 text-sm font-mono font-medium text-gray-700 border-b">
                  {r.file_path}
                </div>
                <ConflictDiffViewer
                  originalContent={r.original_content}
                  resolvedContent={r.resolved_content}
                />
                <div className="px-3 py-2 bg-blue-50 border-t text-sm prose prose-sm max-w-none">
                  <Markdown>{r.explanation}</Markdown>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3 pt-3 border-t">
            <button
              onClick={handleApplyResolution}
              disabled={applyingResolution}
              className="px-5 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {applyingResolution ? '적용 중...' : 'AI 해결안 승인 및 머지'}
            </button>
            <button
              onClick={() => setConflictResult(null)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
            >
              취소
            </button>
            <span className="text-xs text-gray-500">AI 해결안을 확인한 후 승인하면 main에 머지됩니다</span>
          </div>
        </div>
      )}

      {/* 배포 파이프라인 진행 상태 */}
      {buildStatus && (
        <div ref={pipelineRef} className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">배포 파이프라인</h3>
            {currentDeployment && (
              <span className="text-xs text-gray-400 font-mono">
                ID: {currentDeployment.id} | {currentDeployment.branch}
              </span>
            )}
          </div>
          <DeployPipeline stages={stages} buildStatus={buildStatus} />
        </div>
      )}

      {/* 실시간 빌드 로그 */}
      {currentDeployment && buildLog.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <h3 className="font-semibold text-gray-800 mb-3">빌드 로그 (실시간)</h3>
          <BuildLogStream lines={buildLog} />
          {rcaReport && (
            <div className="mt-4">
              <RCAReportComponent report={rcaReport} />
            </div>
          )}
        </div>
      )}

      <div className="mt-6 bg-orange-50 border border-orange-200 rounded-xl p-4">
        <p className="text-sm font-semibold text-orange-800 mb-1">&#9888; 패키지 변경 시 주의</p>
        <p className="text-xs text-gray-700">
          <code className="bg-gray-200 px-1 rounded">pip install</code> / <code className="bg-gray-200 px-1 rounded">npm install</code> 이 필요한 변경은
          <span className="font-semibold text-orange-700"> 폐쇄망 환경에서 배포 실패</span>할 수 있습니다.
          패키지 변경 시 로컬에서 테스트 후 이미지 재빌드(<code className="bg-gray-200 px-1 rounded">export-images.sh</code>)가 필요합니다.
        </p>
      </div>
    </div>
  );
}
