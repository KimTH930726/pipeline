import { useState, useEffect } from 'react';
import { fetchBranches } from '../../api/gitApi';
import type { BranchInfo } from '../../types/git';

interface Props {
  onSelect: (branch: string) => void;
  selected?: string;
  excludeMain?: boolean;
}

export default function BranchSelector({ onSelect, selected, excludeMain = false }: Props) {
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBranches()
      .then((b) => setBranches(excludeMain ? b.filter((x) => x.name !== 'main') : b))
      .catch(() => setBranches([]))
      .finally(() => setLoading(false));
  }, [excludeMain]);

  if (loading) return <div className="text-sm text-gray-500">브랜치 로딩 중...</div>;

  return (
    <select
      value={selected || ''}
      onChange={(e) => onSelect(e.target.value)}
      className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
    >
      <option value="">브랜치 선택</option>
      {branches.map((b) => (
        <option key={b.name} value={b.name}>
          {b.name} {b.is_active ? '(active)' : ''} - {b.last_commit_sha}
        </option>
      ))}
    </select>
  );
}
