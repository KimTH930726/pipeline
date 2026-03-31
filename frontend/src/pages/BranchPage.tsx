import { useState, useEffect, useCallback } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import Header from '../components/layout/Header';
import { fetchBranches, createBranch, deleteBranch } from '../api/gitApi';
import type { BranchInfo } from '../types/git';

export default function BranchPage() {
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const [baseBranch, setBaseBranch] = useState('');
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadBranches = useCallback(() => {
    setLoading(true);
    fetchBranches()
      .then(setBranches)
      .catch(() => setBranches([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadBranches(); }, [loadBranches]);
  useAutoRefresh(loadBranches);

  const handleCreate = async () => {
    if (!newName.trim() || !baseBranch) return;
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      await createBranch(newName.trim(), baseBranch);
      setSuccess(`'${newName.trim()}' 브랜치가 '${baseBranch}' 기준으로 생성되었습니다.`);
      setNewName('');
      setBaseBranch('');
      loadBranches();
    } catch (e: any) {
      setError(e.response?.data?.message || '브랜치 생성 실패');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (branchName: string) => {
    if (!confirm(`'${branchName}' 브랜치를 삭제하시겠습니까?`)) return;
    setError('');
    setSuccess('');
    try {
      await deleteBranch(branchName);
      setSuccess(`'${branchName}' 브랜치가 삭제되었습니다.`);
      loadBranches();
    } catch (e: any) {
      setError(e.response?.data?.message || '브랜치 삭제 실패');
    }
  };

  return (
    <div>
      <Header title="브랜치 관리" subtitle="브랜치 생성, 삭제 및 현황 조회" />

      {/* 브랜치 생성 */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">새 브랜치 생성</h2>
        <div className="flex items-center gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">기준 브랜치</label>
            <select
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[180px]"
            >
              <option value="">선택</option>
              {branches.map((b) => (
                <option key={b.name} value={b.name}>{b.name}</option>
              ))}
            </select>
          </div>
          <span className="text-gray-400 text-lg mt-5">&rarr;</span>
          <div>
            <label className="block text-xs text-gray-500 mb-1">새 브랜치 이름</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              placeholder="feature/my-branch"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-64 focus:ring-2 focus:ring-green-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !newName.trim() || !baseBranch}
            className="mt-5 px-5 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {creating ? '생성 중...' : '생성'}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {success && <p className="mt-3 text-sm text-green-600">{success}</p>}
      </div>

      {/* 브랜치 목록 */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="p-4 bg-gray-50 border-b">
          <h2 className="text-sm font-semibold text-gray-700">브랜치 목록 ({branches.length})</h2>
        </div>
        {loading ? (
          <div className="p-6 text-center text-sm text-gray-500">로딩 중...</div>
        ) : branches.length === 0 ? (
          <div className="p-6 text-center text-sm text-gray-500">브랜치가 없습니다.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b bg-gray-50">
                <th className="px-4 py-3 font-medium">브랜치</th>
                <th className="px-4 py-3 font-medium">상태</th>
                <th className="px-4 py-3 font-medium">최근 커밋</th>
                <th className="px-4 py-3 font-medium">커밋 메시지</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {branches.map((b) => (
                <tr key={b.name} className="border-b last:border-b-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">
                    {b.name}
                  </td>
                  <td className="px-4 py-3">
                    {b.is_active ? (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">active</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">inactive</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">
                    {b.last_commit_sha || '-'}
                  </td>
                  <td className="px-4 py-3 text-gray-600 truncate max-w-xs">
                    {b.last_commit_message || '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {b.name !== 'main' && (
                      <button
                        onClick={() => handleDelete(b.name)}
                        className="px-3 py-1 text-xs text-red-600 hover:bg-red-50 rounded border border-red-200"
                      >
                        삭제
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
