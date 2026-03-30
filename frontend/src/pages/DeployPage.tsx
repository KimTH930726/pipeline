import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import BuildStatusBadge from '../components/deploy/BuildStatusBadge';
import BuildLogStream from '../components/deploy/BuildLogStream';
import ChangedFileList from '../components/git/ChangedFileList';
import DiffViewer from '../components/git/DiffViewer';
import RCAReportComponent from '../components/analysis/RCAReport';
import { triggerDeploy, fetchRecentDeploys, fetchDeployStatus, triggerRollback, markRolledBack } from '../api/deployApi';
import type { DeployPage as DeployPageType } from '../api/deployApi';
import { listApprovedReviews, type ReviewResponse } from '../api/reviewApi';
import { fetchChangedFiles, fetchDiff } from '../api/gitApi';
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

  // 페이징
  const [deployPage, setDeployPage] = useState<DeployPageType>({ items: [], total: 0, page: 1, size: 10 });
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // 이력 상세 (토글)
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<DeployDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);

  const { currentDeployment, buildLog, rcaReport, buildStatus, setDeployment } = useDeployStore();
  useBuildStatus(currentDeployment?.id ?? null);

  const loadDeploys = (page = 1) => {
    fetchRecentDeploys(page, pageSize).then(setDeployPage).catch(() => {});
  };

  const reload = () => {
    listApprovedReviews()
      .then(setApprovedBranches)
      .catch(() => setApprovedBranches([]))
      .finally(() => setLoadingApproved(false));
    loadDeploys(currentPage);
  };

  useEffect(() => { reload(); }, []);

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
    try {
      const deployment = await triggerDeploy(selectedBranch);
      setDeployment(deployment);
    } catch (err) {
      console.error('Deploy failed:', err);
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
      await triggerRollback(expandedDetail.branch, expandedDetail.commit_sha || undefined);
      await markRolledBack(expandedDetail.id);
      setExpandedDetail({ ...expandedDetail, rolled_back: true });
      loadDeploys(currentPage);
    } catch (err) {
      console.error('Rollback failed:', err);
    } finally {
      setRollingBack(false);
    }
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
              disabled={!selectedBranch || buildStatus === 'BUILDING'}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {buildStatus === 'BUILDING' ? '빌드 중...' : '배포 실행'}
            </button>
            {buildStatus && <BuildStatusBadge status={buildStatus} />}
          </div>
        )}
        <p className="mt-2 text-xs text-gray-400">
          빌드 성공 시 자동으로 main에 머지되고, Docker가 재빌드/재기동됩니다.
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

      {/* 실시간 빌드 로그 */}
      {currentDeployment && buildLog.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-800">빌드 로그 (실시간)</h3>
            <span className="text-xs text-gray-400 font-mono">
              ID: {currentDeployment.id} | {currentDeployment.branch}
            </span>
          </div>
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
        </div>
        {deployPage.items.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">배포 이력이 없습니다.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2">ID</th>
                <th className="pb-2">브랜치</th>
                <th className="pb-2">상태</th>
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
                    <td className="py-2 font-mono">{d.id}</td>
                    <td className="py-2 font-mono">{d.branch}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-1">
                        <BuildStatusBadge status={d.status} />
                        {d.rolled_back && (
                          <span className="px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded text-xs">원복</span>
                        )}
                      </div>
                    </td>
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
                      <td colSpan={6} className="p-4 bg-gray-50 border-b">
                        {loadingDetail ? (
                          <p className="text-sm text-gray-500">로딩 중...</p>
                        ) : expandedDetail ? (
                          <div>
                            <div className="text-xs text-gray-500 mb-3">
                              커밋: <span className="font-mono">{expandedDetail.commit_sha || '-'}</span> |
                              시작: {expandedDetail.started_at ? new Date(expandedDetail.started_at).toLocaleString('ko-KR') : '-'} |
                              종료: {expandedDetail.finished_at ? new Date(expandedDetail.finished_at).toLocaleString('ko-KR') : '-'}
                            </div>
                            {expandedDetail.build_log && (
                              <BuildLogStream lines={expandedDetail.build_log.split('\n')} />
                            )}
                            {(expandedDetail.status === 'SUCCESS' || expandedDetail.status === 'FAILED') && !expandedDetail.rolled_back && (
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
    </div>
  );
}
