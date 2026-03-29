import { useState } from 'react';
import Header from '../components/layout/Header';
import BranchSelector from '../components/git/BranchSelector';
import BuildStatusBadge from '../components/deploy/BuildStatusBadge';
import BuildLogStream from '../components/deploy/BuildLogStream';
import RCAReportComponent from '../components/analysis/RCAReport';
import RollbackButton from '../components/analysis/RollbackButton';
import { triggerDeploy, fetchRecentDeploys } from '../api/deployApi';
import { useBuildStatus } from '../hooks/useBuildStatus';
import { useDeployStore } from '../store/deployStore';
import type { DeployStatus } from '../types/deploy';
import { useEffect } from 'react';

export default function DeployPage() {
  const [branch, setBranch] = useState('');
  const [recentDeploys, setRecentDeploys] = useState<DeployStatus[]>([]);
  const { currentDeployment, buildLog, rcaReport, buildStatus, setDeployment } = useDeployStore();

  useBuildStatus(currentDeployment?.id ?? null);

  useEffect(() => {
    fetchRecentDeploys().then(setRecentDeploys).catch(() => {});
  }, []);

  const handleDeploy = async () => {
    if (!branch) return;
    try {
      const deployment = await triggerDeploy(branch);
      setDeployment(deployment);
    } catch (err) {
      console.error('Deploy failed:', err);
    }
  };

  return (
    <div>
      <Header title="배포" subtitle="빌드 실행, 실시간 로그 모니터링, AI 실패 분석" />

      <div className="flex items-center gap-4 mb-6">
        <BranchSelector selected={branch} onSelect={setBranch} />
        <button
          onClick={handleDeploy}
          disabled={!branch || buildStatus === 'BUILDING'}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          배포 실행
        </button>
        {buildStatus && <BuildStatusBadge status={buildStatus} />}
      </div>

      {currentDeployment && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-800">빌드 로그</h3>
              <span className="text-xs text-gray-400 font-mono">
                ID: {currentDeployment.id} | {currentDeployment.branch}
              </span>
            </div>
            <BuildLogStream lines={buildLog} />
          </div>

          {rcaReport && (
            <div className="space-y-4">
              <RCAReportComponent report={rcaReport} />
              <div className="flex items-center gap-4">
                <RollbackButton
                  branch={currentDeployment.branch}
                  onRollback={() => {
                    fetchRecentDeploys().then(setRecentDeploys).catch(() => {});
                  }}
                />
                <span className="text-sm text-gray-500">
                  AI가 분석한 원인을 확인 후 원복 여부를 결정하세요
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {recentDeploys.length > 0 && (
        <div className="mt-8 bg-white border border-gray-200 rounded-xl p-4">
          <h3 className="font-semibold text-gray-800 mb-3">최근 배포 이력</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2">ID</th>
                <th className="pb-2">브랜치</th>
                <th className="pb-2">상태</th>
                <th className="pb-2">커밋</th>
                <th className="pb-2">시작</th>
              </tr>
            </thead>
            <tbody>
              {recentDeploys.map((d) => (
                <tr key={d.id} className="border-b border-gray-100">
                  <td className="py-2 font-mono">{d.id}</td>
                  <td className="py-2 font-mono">{d.branch}</td>
                  <td className="py-2">
                    <BuildStatusBadge status={d.status} />
                  </td>
                  <td className="py-2 font-mono text-xs">{d.commit_sha?.slice(0, 8) || '-'}</td>
                  <td className="py-2 text-xs text-gray-500">
                    {d.started_at ? new Date(d.started_at).toLocaleString('ko-KR') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
