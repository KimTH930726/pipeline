import { useState, useEffect, useCallback } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { Box, Trash2, ExternalLink, RefreshCw } from 'lucide-react';
import Header from '../components/layout/Header';
import { fetchBranches } from '../api/gitApi';
import type { BranchInfo } from '../types/git';
import client from '../api/client';

interface SandboxInfo {
  id: number;
  branch: string;
  backend_port: number;
  frontend_port: number;
  status: string;
  error_log: string;
}

export default function SandboxPage() {
  const [branch, setBranch] = useState('');
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [sandboxes, setSandboxes] = useState<SandboxInfo[]>([]);
  const [creating, setCreating] = useState(false);

  const loadData = useCallback(() => {
    client.get<SandboxInfo[]>('/sandbox/').then((r) => setSandboxes(r.data)).catch(() => {});
    fetchBranches().then((b) => setBranches(b.filter((x) => x.name !== 'main'))).catch(() => {});
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  useAutoRefresh(loadData);

  // CREATING 상태가 있으면 3초마다 자동 polling
  useEffect(() => {
    const hasCreating = sandboxes.some((s) => s.status === 'CREATING');
    if (!hasCreating) return;
    const timer = setInterval(() => {
      client.get<SandboxInfo[]>('/sandbox/').then((r) => setSandboxes(r.data)).catch(() => {});
    }, 3000);
    return () => clearInterval(timer);
  }, [sandboxes]);

  const handleCreate = async () => {
    if (!branch) return;
    setCreating(true);
    try {
      await client.post('/sandbox/', { branch });
      setTimeout(() => {
        client.get<SandboxInfo[]>('/sandbox/').then((r) => setSandboxes(r.data)).catch(() => {});
      }, 2000);
    } finally {
      setCreating(false);
    }
  };



  const handleDestroy = async (id: number) => {
    if (!confirm('샌드박스를 삭제하시겠습니까? 컨테이너와 임시 파일이 모두 제거됩니다.')) return;
    await client.delete(`/sandbox/${id}`);
    loadData();
  };

  const statusStyle = (status: string) => {
    const map: Record<string, string> = {
      RUNNING: 'bg-green-100 text-green-700',
      CREATING: 'bg-yellow-100 text-yellow-700',
      STOPPED: 'bg-gray-100 text-gray-600',
      ERROR: 'bg-red-100 text-red-700',
    };
    return map[status] || 'bg-gray-100 text-gray-600';
  };

  const statusLabel: Record<string, string> = {
    RUNNING: '실행 중',
    CREATING: '생성 중',
    STOPPED: '중지됨',
    ERROR: '오류',
  };

  return (
    <div>
      <Header title="샌드박스" subtitle="브랜치별 독립 테스트 환경 (Backend + Frontend)" />

      <div className="flex items-center gap-4 mb-6">
        <select
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          <option value="">브랜치 선택 (main 제외)</option>
          {branches.map((b) => (
            <option key={b.name} value={b.name}>{b.name}</option>
          ))}
        </select>
        <button
          onClick={handleCreate}
          disabled={!branch || creating}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
        >
          {creating ? '생성 중...' : '샌드박스 생성'}
        </button>
        <button
          onClick={loadData}
          className="px-3 py-2 text-gray-500 hover:text-gray-700"
          title="새로고침"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {sandboxes.map((s) => (
          <div key={s.id} className={`bg-white border rounded-xl p-5 ${s.status === 'CREATING' ? 'border-yellow-300' : 'border-gray-200'}`}>
            {s.status === 'CREATING' && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="animate-spin h-4 w-4 border-2 border-yellow-500 border-t-transparent rounded-full" />
                  <span className="text-sm font-medium text-yellow-700">샌드박스 생성 중...</span>
                </div>
                <div className="text-xs text-gray-500 mb-2">브랜치 소스 추출 → 컨테이너 기동 → 헬스체크</div>
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-yellow-500 h-2 rounded-full animate-pulse" style={{ width: '60%' }} />
                </div>
              </div>
            )}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Box size={18} className={s.status === 'RUNNING' ? 'text-green-600' : s.status === 'ERROR' ? 'text-red-500' : 'text-yellow-500'} />
                <span className="font-mono text-sm font-medium">{s.branch}</span>
              </div>
              {s.status !== 'CREATING' && (
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusStyle(s.status)}`}>
                  {statusLabel[s.status] || s.status}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Backend</p>
                <p className="font-mono text-sm">:{s.backend_port}</p>
                {s.status === 'RUNNING' && (
                  <a
                    href={`http://localhost:${s.backend_port}/docs`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-blue-600 hover:underline mt-1"
                  >
                    <ExternalLink size={10} /> API Docs
                  </a>
                )}
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Frontend</p>
                <p className="font-mono text-sm">:{s.frontend_port}</p>
                {s.status === 'RUNNING' && (
                  <a
                    href={`http://localhost:${s.frontend_port}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-blue-600 hover:underline mt-1"
                  >
                    <ExternalLink size={10} /> 열기
                  </a>
                )}
              </div>
            </div>

            {s.status === 'ERROR' && s.error_log && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                <p className="text-xs font-semibold text-red-600 mb-1">오류 원인</p>
                <pre className="text-xs text-red-700 whitespace-pre-wrap">{s.error_log}</pre>
              </div>
            )}

            <div className="flex items-center gap-2 border-t pt-3">
              <button
                onClick={() => handleDestroy(s.id)}
                className="flex items-center gap-1 text-xs px-3 py-1.5 text-red-600 hover:bg-red-50 rounded border border-red-200 ml-auto"
              >
                <Trash2 size={12} /> 삭제
              </button>
            </div>
          </div>
        ))}
        {sandboxes.length === 0 && (
          <p className="col-span-2 text-sm text-gray-400 text-center py-8">활성 샌드박스가 없습니다.</p>
        )}
      </div>

      <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-700">
        <p className="font-semibold mb-1">샌드박스 제한사항</p>
        <ul className="list-disc ml-4 space-y-0.5 text-xs">
          <li>소스 코드 변경만 반영됩니다 (Python/React 소스 수정)</li>
          <li>패키지 추가(pip install, npm install)가 필요한 변경은 샌드박스에서 동작하지 않습니다</li>
          <li>패키지 변경이 포함된 브랜치는 로컬 환경에서 직접 테스트하세요</li>
          <li>DB/Redis는 운영 환경과 공유됩니다</li>
        </ul>
      </div>
    </div>
  );
}
