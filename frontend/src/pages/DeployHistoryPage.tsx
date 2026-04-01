import { useState, useEffect, useCallback, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import Header from '../components/layout/Header';
import BuildStatusBadge from '../components/deploy/BuildStatusBadge';
import BuildLogStream from '../components/deploy/BuildLogStream';
import { fetchRecentDeploys, fetchDeployStatus, triggerRollback, markRolledBack, compareDeploys } from '../api/deployApi';
import type { DeployPage as DeployPageType, DeployCompare } from '../api/deployApi';
import type { DeployStatus, DeployDetail } from '../types/deploy';
import { useDeployStore } from '../store/deployStore';

export default function DeployHistoryPage() {
  const navigate = useNavigate();
  const { startPipeline, setDeployment, updateStage } = useDeployStore();

  // 페이징
  const [deployPage, setDeployPage] = useState<DeployPageType>({ items: [], total: 0, page: 1, size: 10 });
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // 필터
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // 이력 상세 (토글)
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<DeployDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);
  const [showBuildLog, setShowBuildLog] = useState(false);

  // 배포 비교
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelections, setCompareSelections] = useState<number[]>([]);
  const [compareResult, setCompareResult] = useState<DeployCompare | null>(null);
  const [comparing, setComparing] = useState(false);

  const loadDeploys = useCallback((page = 1) => {
    fetchRecentDeploys(
      page,
      pageSize,
      undefined,
      statusFilter || undefined,
      dateFrom || undefined,
      dateTo || undefined,
    ).then(setDeployPage).catch(() => {});
  }, [statusFilter, dateFrom, dateTo]);

  const reload = useCallback(() => {
    loadDeploys(currentPage);
  }, [currentPage, loadDeploys]);

  useEffect(() => { reload(); }, [reload]);
  useAutoRefresh(reload);

  const handleToggleDetail = async (deploy: DeployStatus) => {
    setShowBuildLog(false);
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
        navigate('/deploy');
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
      const [a, b] = [...compareSelections].sort((x, y) => x - y);
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

  const handleFilterChange = () => {
    setCurrentPage(1);
    setExpandedId(null);
    setExpandedDetail(null);
  };

  const totalPages = Math.ceil(deployPage.total / pageSize);

  return (
    <div>
      <Header title="배포 이력" subtitle="배포/원복 이력 조회 및 관리" />

      {/* 필터 */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); handleFilterChange(); }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="">전체 상태</option>
          <option value="SUCCESS">성공</option>
          <option value="FAILED">실패</option>
          <option value="BUILDING">빌드 중</option>
        </select>
        <div className="flex items-center gap-1">
          <label className="text-xs text-gray-500">시작일</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); handleFilterChange(); }}
            className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm bg-white"
          />
        </div>
        <div className="flex items-center gap-1">
          <label className="text-xs text-gray-500">종료일</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); handleFilterChange(); }}
            className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm bg-white"
          />
        </div>
        <span className="text-sm text-gray-500">총 {deployPage.total}건</span>
      </div>

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
                <Fragment key={d.id}>
                  <tr
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
                    <tr>
                      <td colSpan={compareMode ? 8 : 7} className="p-4 bg-gray-50 border-b">
                        {loadingDetail ? (
                          <p className="text-sm text-gray-500">로딩 중...</p>
                        ) : expandedDetail ? (
                          <div>
                            <div className="grid grid-cols-3 gap-3 mb-3 bg-white rounded-lg border border-gray-200 p-3">
                              <div>
                                <p className="text-xs text-gray-400">커밋</p>
                                <p className="font-mono text-sm text-gray-800 mt-0.5">{expandedDetail.commit_sha?.slice(0, 8) || '-'}</p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-400">시작</p>
                                <p className="text-sm text-gray-800 mt-0.5">{expandedDetail.started_at ? new Date(expandedDetail.started_at).toLocaleString('ko-KR') : '-'}</p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-400">종료</p>
                                <p className="text-sm text-gray-800 mt-0.5">{expandedDetail.finished_at ? new Date(expandedDetail.finished_at).toLocaleString('ko-KR') : '-'}</p>
                              </div>
                            </div>
                            {expandedDetail.commit_messages && (
                              <div className="mb-3 bg-white rounded-lg border border-gray-200 p-3">
                                <p className="text-xs font-medium text-gray-400 mb-1">커밋 메시지</p>
                                <p className="text-sm text-gray-800 font-mono">{expandedDetail.commit_messages}</p>
                              </div>
                            )}
                            {expandedDetail.changed_files.length > 0 && (
                              <div className="mb-3 bg-white rounded-lg border border-gray-200 overflow-hidden">
                                <p className="text-xs font-medium text-gray-400 px-3 py-2 border-b border-gray-100">변경 파일 ({expandedDetail.changed_files.length}개)</p>
                                {expandedDetail.changed_files.map((f, i) => (
                                  <p key={i} className="text-xs font-mono text-gray-700 px-3 py-1.5 border-b border-gray-50 last:border-b-0 hover:bg-blue-50">{f}</p>
                                ))}
                              </div>
                            )}
                            {expandedDetail.error_log && (
                              <div className="mb-3 bg-red-50 rounded-lg border border-red-200 p-3">
                                <p className="text-xs font-medium text-red-500 mb-1">에러</p>
                                <pre className="text-xs text-red-700 whitespace-pre-wrap">{expandedDetail.error_log}</pre>
                              </div>
                            )}
                            {expandedDetail.build_log && (
                              <div className="mb-3">
                                <button
                                  onClick={(e) => { e.stopPropagation(); setShowBuildLog(!showBuildLog); }}
                                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mb-2"
                                >
                                  <span className={`transition-transform ${showBuildLog ? 'rotate-90' : ''}`}>&#9654;</span>
                                  빌드 로그 {showBuildLog ? '접기' : '보기'}
                                </button>
                                {showBuildLog && (
                                  <BuildLogStream lines={expandedDetail.build_log.split('\n')} />
                                )}
                              </div>
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
                </Fragment>
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
    </div>
  );
}
