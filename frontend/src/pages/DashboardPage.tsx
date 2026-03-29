import { useState, useEffect } from 'react';
import { Play, AlertTriangle, RotateCcw } from 'lucide-react';
import Header from '../components/layout/Header';
import { fetchRecentDeploys } from '../api/deployApi';
import { fetchAuditTimeline } from '../api/auditApi';
import type { DeployStatus } from '../types/deploy';
import type { AuditEntry } from '../types/audit';

export default function DashboardPage() {
  const [deploys, setDeploys] = useState<DeployStatus[]>([]);
  const [audits, setAudits] = useState<AuditEntry[]>([]);

  useEffect(() => {
    fetchRecentDeploys().then(setDeploys).catch(() => {});
    fetchAuditTimeline({ limit: 10 }).then((t) => setAudits(t.entries)).catch(() => {});
  }, []);

  const successCount = deploys.filter((d) => d.status === 'SUCCESS').length;
  const failCount = deploys.filter((d) => d.status === 'FAILED').length;
  const rollbackCount = audits.filter((a) => a.event_type === 'ROLLBACK').length;

  const cards = [
    { label: '최근 배포', value: deploys.length, icon: Play, color: 'bg-blue-500' },
    { label: '성공', value: successCount, icon: Play, color: 'bg-green-500' },
    { label: '실패', value: failCount, icon: AlertTriangle, color: 'bg-red-500' },
    { label: '원복', value: rollbackCount, icon: RotateCcw, color: 'bg-orange-500' },
  ];

  return (
    <div>
      <Header title="대시보드" subtitle="배포 현황 및 시스템 상태 모니터링" />

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

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-800 mb-3">최근 배포</h3>
          {deploys.length === 0 ? (
            <p className="text-sm text-gray-400">배포 이력 없음</p>
          ) : (
            <div className="space-y-2">
              {deploys.slice(0, 5).map((d) => (
                <div key={d.id} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-gray-600">{d.branch}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    d.status === 'SUCCESS' ? 'bg-green-100 text-green-700' :
                    d.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {d.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-800 mb-3">최근 이벤트</h3>
          {audits.length === 0 ? (
            <p className="text-sm text-gray-400">이벤트 없음</p>
          ) : (
            <div className="space-y-2">
              {audits.slice(0, 5).map((a) => (
                <div key={a.id} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">{a.event_type}</span>
                  <span className="text-xs text-gray-400 font-mono">{a.branch}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
