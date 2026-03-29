import { useState, useEffect } from 'react';
import { Box, Trash2, ExternalLink } from 'lucide-react';
import Header from '../components/layout/Header';
import BranchSelector from '../components/git/BranchSelector';
import client from '../api/client';

interface SandboxInfo {
  id: number;
  branch: string;
  port: number;
  status: string;
}

export default function SandboxPage() {
  const [branch, setBranch] = useState('');
  const [sandboxes, setSandboxes] = useState<SandboxInfo[]>([]);
  const [creating, setCreating] = useState(false);

  const loadSandboxes = () => {
    client.get<SandboxInfo[]>('/sandbox/').then((r) => setSandboxes(r.data)).catch(() => {});
  };

  useEffect(() => { loadSandboxes(); }, []);

  const handleCreate = async () => {
    if (!branch) return;
    setCreating(true);
    try {
      await client.post('/sandbox/', { branch });
      loadSandboxes();
    } finally {
      setCreating(false);
    }
  };

  const handleDestroy = async (id: number) => {
    await client.delete(`/sandbox/${id}`);
    loadSandboxes();
  };

  return (
    <div>
      <Header title="샌드박스" subtitle="브랜치별 독립 테스트 환경 관리" />

      <div className="flex items-center gap-4 mb-6">
        <BranchSelector selected={branch} onSelect={setBranch} />
        <button
          onClick={handleCreate}
          disabled={!branch || creating}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
        >
          {creating ? '생성 중...' : '샌드박스 생성'}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {sandboxes.map((s) => (
          <div key={s.id} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Box size={18} className="text-green-600" />
                <span className="font-mono text-sm">{s.branch}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${
                s.status === 'RUNNING' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {s.status}
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-3">Port: {s.port}</p>
            <div className="flex items-center gap-2">
              <a
                href={`http://localhost:${s.port}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
              >
                <ExternalLink size={12} /> 열기
              </a>
              <button
                onClick={() => handleDestroy(s.id)}
                className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 ml-auto"
              >
                <Trash2 size={12} /> 삭제
              </button>
            </div>
          </div>
        ))}
        {sandboxes.length === 0 && (
          <p className="col-span-3 text-sm text-gray-400 text-center py-8">활성 샌드박스가 없습니다.</p>
        )}
      </div>
    </div>
  );
}
