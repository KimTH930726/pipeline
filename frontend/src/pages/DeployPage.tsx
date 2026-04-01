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
import { triggerDeploy, fetchRecentDeploys, fetchDeployStatus, triggerRollback, markRolledBack, compareDeploys } from '../api/deployApi';
import type { DeployPage as DeployPageType, DeployCompare } from '../api/deployApi';
import { listApprovedReviews, type ReviewResponse } from '../api/reviewApi';
import Markdown from 'react-markdown';
import { fetchChangedFiles, fetchDiff, checkConflicts, applyResolution } from '../api/gitApi';
import type { MergeConflictResponse } from '../api/gitApi';
import { useBuildStatus } from '../hooks/useBuildStatus';
import { useDeployStore } from '../store/deployStore';
import type { DeployStatus, DeployDetail } from '../types/deploy';
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

  // 페이징
  const [deployPage, setDeployPage] = useState<DeployPageType>({ items: [], total: 0, page: 1, size: 10 });
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // 이력 상세 (토글)
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<DeployDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);

  // 배포 비교
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelections, setCompareSelections] = useState<number[]>([]);
  const [compareResult, setCompareResult] = useState<DeployCompare | null>(null);
  const [comparing, setComparing] = useState(false);

  const { currentDeployment, buildLog, rcaReport, buildStatus, stages, startPipeline, setDeployment, updateStage } = useDeployStore();
  const pipelineRef = useRef<HTMLDivElement>(null);
  useBuildStatus(currentDeployment?.id ?? null);

  const loadDeploys = (page = 1) => {
    fetchRecentDeploys(page, pageSize).then(setDeployPage).catch(() => {});
  };

  const reload = useCallback(() => {
    listApprovedReviews()
      .then(setApprovedBranches)
      .catch(() => setApprovedBranches([]))
      .finally(() => setLoadingApproved(false));
    loadDeploys(currentPage);
  }, [currentPage]);

  useEffect(() => { reload(); }, [reload]);
  useAutoRefresh(reload);

  // 빌드 중이면 3초마다 이력 갱신, 완료/실패 시 즉시 갱신
  useEffect(() => {
    if (buildStatus === 'SUCCESS' || buildStatus === 'FAILED') {
      loadDeploys(currentPage);
      return;
    }
    if (buildStatus !== 'BUILDING') return;
    const timer = setInterval(() => loadDeploys(currentPage), 3000);
    return () => clearInterval(timer);
  }, [buildStatus, currentPage]);

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
    } catch { /* 충돌 체크 실패 시 배포 진행 */ }
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

  const handleToggleDetail = async (deploy: DeployStatus) => {
    if (expandedId === deploy.id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(deploy.id);
    setExpandedDetail(null);
    setLoadingDetail(true);
    try {
      const detail = await fetchDeployStatus(deploy.id);
      setExpandedDetail(detail);
    } catch { /* ignore */ }
    finally { setLoadingDetail(false); }
  };

  const handleRollback = async () => {
    if (!expandedDetail) return;
    if (!confirm(`배포 #${expandedDetail.id} (${expandedDetail.branch})를 원복하시겠습니까?`)) return;
    setRollingBack(true);
    try {
      const result = await triggerRollback(expandedDetail.branch, expandedDetail.commit_sha || undefined);
      await markRolledBack(expandedDetail.id);
      setExpandedDetail({ ...expandedDetail, rolled_back: true });
      loadDeploys(currentPage);

      // 원복 재배포 파이프라인 UI 연결
      if (result.deployment_id) {
        startPipeline();
        updateStage('CONFLICT_CHECK', 'completed');
        setDeployment({
          id: result.deployment_id,
          branch: expandedDetail.branch,
          commit_sha: result.new_commit,
          status: 'BUILDING',
          rolled_back: false,
          acted_by: null,
          commit_messages: `[원복] ${result.reverted_to.slice(0, 8)} 으로 되돌림`,
          started_at: new Date().toISOString(),
          finished_at: null,
        });
        setTimeout(() => pipelineRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      }
    } catch (err) {
      console.error('Rollback failed:', err);
    } finally {
      setRollingBack(false);
    }
  };

  const handleToggleCompare = (id: number) => {
    setCompareSelections((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleCompare = async () => {
    if (compareSelections.length !== 2) return;
    setComparing(true);
    try {
      const [a, b] = compareSelections.sort((x, y) => x - y);
      const result = await compareDeploys(a, b);
      setCompareResult(result);
    } catch { setCompareResult(null); }
    finally { setComparing(false); }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    setExpandedId(null);
    setExpandedDetail(null);
    loadDeploys(page);
  };

  const totalPages = Math.ceil(deployPage.total / pageSize);

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

      {/* 배포 이력 + 토글 상세 */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-800">배포 이력 ({deployPage.total}건)</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setCompareMode(!compareMode); setCompareSelections([]); setCompareResult(null); }}
              className={`px-3 py-1 text-xs rounded border ${compareMode ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 hover:bg-gray-50'}`}
            >
              {compareMode ? '비교 모드 종료' : '배포 비교'}
            </button>
            {compareMode && compareSelections.length === 2 && (
              <button
                onClick={handleCompare}
                disabled={comparing}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {comparing ? '비교 중...' : '비교 실행'}
              </button>
            )}
            {compareMode && <span className="text-xs text-gray-400">{compareSelections.length}/2 선택</span>}
          </div>
        </div>
        {deployPage.items.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">배포 이력이 없습니다.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                {compareMode && <th className="pb-2 w-8"></th>}
                <th className="pb-2">ID</th>
                <th className="pb-2">브랜치</th>
                <th className="pb-2">상태</th>
                <th className="pb-2">수행자</th>
                <th className="pb-2">커밋</th>
                <th className="pb-2">시작</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {deployPage.items.map((d) => (
                <>
                  <tr
                    key={d.id}
                    className={`border-b border-gray-100 cursor-pointer hover:bg-blue-50 transition-colors ${
                      expandedId === d.id ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => handleToggleDetail(d)}
                  >
                    {compareMode && (
                    <td className="py-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={compareSelections.includes(d.id)}
                        onChange={() => handleToggleCompare(d.id)}
                        className="rounded"
                      />
                    </td>
                  )}
                  <td className="py-2 font-mono">{d.id}</td>
                    <td className="py-2 font-mono">{d.branch}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-1">
                        <BuildStatusBadge status={d.status} />
                        {d.rolled_back && (
                          <span className="px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded text-xs">원복</span>
                        )}
                        {d.commit_messages?.startsWith('[원복]') && (
                          <span className="px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded text-xs">원복 배포</span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 text-xs text-gray-600">{d.acted_by || '-'}</td>
                  <td className="py-2 font-mono text-xs">{d.commit_sha?.slice(0, 8) || '-'}</td>
                    <td className="py-2 text-xs text-gray-500">
                      {d.started_at ? new Date(d.started_at).toLocaleString('ko-KR') : '-'}
                    </td>
                    <td className="py-2 text-xs text-blue-500">
                      {expandedId === d.id ? '접기' : '상세'}
                    </td>
                  </tr>
                  {/* 토글 상세 */}
                  {expandedId === d.id && (
                    <tr key={`detail-${d.id}`}>
                      <td colSpan={compareMode ? 8 : 7} className="p-4 bg-gray-50 border-b">
                        {loadingDetail ? (
                          <p className="text-sm text-gray-500">로딩 중...</p>
                        ) : expandedDetail ? (
                          <div>
                            <div className="text-xs text-gray-500 mb-3">
                              커밋: <span className="font-mono">{expandedDetail.commit_sha || '-'}</span> |
                              시작: {expandedDetail.started_at ? new Date(expandedDetail.started_at).toLocaleString('ko-KR') : '-'} |
                              종료: {expandedDetail.finished_at ? new Date(expandedDetail.finished_at).toLocaleString('ko-KR') : '-'}
                            </div>
                            {expandedDetail.commit_messages && (
                              <div className="mb-3">
                                <p className="text-xs font-medium text-gray-500 mb-1">커밋 메시지</p>
                                <p className="text-sm text-gray-700 font-mono bg-white rounded p-2 border border-gray-200">{expandedDetail.commit_messages}</p>
                              </div>
                            )}
                            {expandedDetail.changed_files.length > 0 && (
                              <div className="mb-3">
                                <p className="text-xs font-medium text-gray-500 mb-1">변경 파일 ({expandedDetail.changed_files.length}개)</p>
                                <div className="bg-white rounded border border-gray-200 divide-y divide-gray-100">
                                  {expandedDetail.changed_files.map((f, i) => (
                                    <p key={i} className="text-xs font-mono text-gray-700 px-3 py-1.5">{f}</p>
                                  ))}
                                </div>
                              </div>
                            )}
                            {expandedDetail.build_log && (
                              <BuildLogStream lines={expandedDetail.build_log.split('\n')} />
                            )}
                            {(expandedDetail.status === 'SUCCESS' || expandedDetail.status === 'FAILED') && !expandedDetail.rolled_back && !expandedDetail.commit_messages?.startsWith('[원복]') && (
                              <div className="flex items-center gap-4 mt-4 pt-3 border-t">
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleRollback(); }}
                                  disabled={rollingBack}
                                  className="px-4 py-1.5 bg-orange-600 text-white rounded-lg text-xs font-medium hover:bg-orange-700 disabled:opacity-50"
                                >
                                  {rollingBack ? '원복 중...' : '원복 실행'}
                                </button>
                                <span className="text-xs text-gray-500">
                                  이 배포를 원복하면 main이 이전 상태로 되돌아갑니다
                                </span>
                              </div>
                            )}
                            {expandedDetail.commit_messages?.startsWith('[원복]') && (
                              <p className="mt-3 pt-3 border-t text-xs text-purple-600">
                                원복으로 인한 재배포입니다. 이 배포에 대한 원복은 지원되지 않습니다.
                              </p>
                            )}
                            {expandedDetail.rolled_back && (
                              <p className="mt-3 pt-3 border-t text-xs text-orange-600">이 배포는 이미 원복되었습니다.</p>
                            )}
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}

        {/* 배포 비교 결과 */}
        {compareResult && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-gray-800">
                배포 비교: #{compareResult.from.id} vs #{compareResult.to.id}
              </h4>
              <button onClick={() => setCompareResult(null)} className="text-xs text-gray-400 hover:text-gray-600">닫기</button>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
              <span className="font-mono bg-red-50 px-2 py-1 rounded">#{compareResult.from.id} {compareResult.from.branch} ({compareResult.from.commit_sha.slice(0,8)})</span>
              <span>&rarr;</span>
              <span className="font-mono bg-green-50 px-2 py-1 rounded">#{compareResult.to.id} {compareResult.to.branch} ({compareResult.to.commit_sha.slice(0,8)})</span>
            </div>
            {compareResult.diff_text ? (
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-auto max-h-[400px]">{compareResult.diff_text}</pre>
            ) : (
              <p className="text-sm text-gray-500">두 배포 간 차이가 없습니다.</p>
            )}
          </div>
        )}

        {/* 페이징 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-30"
            >
              이전
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => handlePageChange(p)}
                className={`px-3 py-1 text-sm border rounded ${
                  p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-100'
                }`}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-30"
            >
              다음
            </button>
          </div>
        )}
      </div>

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
