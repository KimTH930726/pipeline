import { useState, useEffect, useCallback } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { GitMerge, CheckCircle, XCircle, RotateCcw } from 'lucide-react';
import Header from '../components/layout/Header';
import BuildStatusBadge from '../components/deploy/BuildStatusBadge';
import { fetchRecentDeploys, fetchDeployStatus } from '../api/deployApi';
import type { DeployStatus, DeployDetail } from '../types/deploy';

export default function DashboardPage() {
  const [deploys, setDeploys] = useState<DeployStatus[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<DeployDetail | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const loadData = useCallback(() => {
    fetchRecentDeploys(1, 20, undefined, statusFilter || undefined).then((r) => setDeploys(r.items)).catch(() => {});
  }, [statusFilter]);

  useEffect(() => { loadData(); }, [loadData]);
  useAutoRefresh(loadData);

  const successCount = deploys.filter((d) => d.status === 'SUCCESS').length;
  const failCount = deploys.filter((d) => d.status === 'FAILED').length;
  const rollbackCount = deploys.filter((d) => d.rolled_back).length;

  const handleToggle = async (d: DeployStatus) => {
    if (expandedId === d.id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(d.id);
    try {
      const detail = await fetchDeployStatus(d.id);
      setExpandedDetail(detail);
    } catch { setExpandedDetail(null); }
  };

  const cards = [
    { label: '총 배포', value: deploys.length, icon: GitMerge, color: 'bg-blue-500' },
    { label: '성공', value: successCount, icon: CheckCircle, color: 'bg-green-500' },
    { label: '실패', value: failCount, icon: XCircle, color: 'bg-red-500' },
    { label: '원복', value: rollbackCount, icon: RotateCcw, color: 'bg-orange-500' },
  ];

  return (
    <div>
      <Header title="대시보드" subtitle="main 브랜치 배포 현황" />

      <div className="grid grid-cols-4 gap-4 mb-8">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 ${c.color} rounded-lg flex items-center justify-center`}>
                  <Icon size={20} className="text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{c.value}</p>
                  <p className="text-xs text-gray-500">{c.label}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* main 배포 이력 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800">main 브랜치 배포 이력</h3>
          <div className="flex items-center gap-1">
            {[
              { value: '', label: '전체' },
              { value: 'SUCCESS', label: '성공' },
              { value: 'FAILED', label: '실패' },
              { value: 'BUILDING', label: '빌드 중' },
            ].map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  statusFilter === f.value
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        {deploys.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">배포 이력이 없습니다.</p>
        ) : (
          <div className="space-y-0">
            {deploys.map((d) => (
              <div key={d.id}>
                <div
                  className={`flex items-center gap-4 p-3 rounded-lg cursor-pointer transition-colors ${
                    expandedId === d.id ? 'bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => handleToggle(d)}
                >
                  {/* 머지 아이콘 */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    d.status === 'SUCCESS' ? 'bg-green-100' :
                    d.status === 'FAILED' ? 'bg-red-100' : 'bg-gray-100'
                  }`}>
                    <GitMerge size={16} className={
                      d.status === 'SUCCESS' ? 'text-green-600' :
                      d.status === 'FAILED' ? 'text-red-600' : 'text-gray-500'
                    } />
                  </div>

                  {/* 브랜치 → main + 커밋 메시지 */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-mono font-medium text-gray-800">{d.branch}</span>
                      <span className="text-gray-400">&rarr;</span>
                      <span className="font-mono text-gray-600">main</span>
                    </div>
                    {d.commit_messages && (
                      <div className="mt-1 space-y-0.5">
                        {d.commit_messages.split('\n').slice(0, 3).map((msg, i) => (
                          <p key={i} className="text-xs text-gray-500 truncate max-w-md">
                            <span className="text-gray-400 mr-1">&bull;</span>{msg}
                          </p>
                        ))}
                        {d.commit_messages.split('\n').length > 3 && (
                          <p className="text-xs text-gray-400">...외 {d.commit_messages.split('\n').length - 3}건</p>
                        )}
                      </div>
                    )}
                    <div className="text-xs text-gray-400 mt-0.5">
                      {d.acted_by && <span className="mr-2 text-gray-500">{d.acted_by}</span>}
                      {d.started_at ? new Date(d.started_at).toLocaleString('ko-KR') : '-'}
                      {d.commit_sha && <span className="ml-2 font-mono">{d.commit_sha.slice(0, 8)}</span>}
                    </div>
                  </div>

                  {/* 상태 */}
                  <div className="flex items-center gap-2">
                    <BuildStatusBadge status={d.status} />
                    {d.rolled_back && (
                      <span className="px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded text-xs">원복</span>
                    )}
                  </div>

                  <span className="text-xs text-gray-400">{expandedId === d.id ? '접기' : '상세'}</span>
                </div>

                {/* 토글 상세 */}
                {expandedId === d.id && expandedDetail && (
                  <div className="ml-12 mr-4 mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200 text-sm">
                    {expandedDetail.build_log && (
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-2">빌드 로그</p>
                        <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto max-h-[200px] overflow-y-auto">
                          {expandedDetail.build_log}
                        </pre>
                      </div>
                    )}
                    {expandedDetail.error_log && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-red-500 mb-1">에러 로그</p>
                        <pre className="bg-red-50 text-red-700 p-2 rounded text-xs">{expandedDetail.error_log}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
