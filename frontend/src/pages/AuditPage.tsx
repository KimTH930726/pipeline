import { useState, useEffect, useCallback } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import Header from '../components/layout/Header';
import AuditTimelineComponent from '../components/audit/AuditTimeline';
import AuditDetailModal from '../components/audit/AuditDetailModal';
import { fetchAuditTimeline } from '../api/auditApi';
import { fetchBranches } from '../api/gitApi';
import type { AuditEntry } from '../types/audit';
import type { BranchInfo } from '../types/git';

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<AuditEntry | null>(null);
  const [eventFilter, setEventFilter] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    fetchBranches().then(setBranches).catch(() => {});
  }, []);

  const loadAudit = useCallback(() => {
    fetchAuditTimeline({
      event_type: eventFilter || undefined,
      branch: branchFilter || undefined,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    })
      .then((t) => {
        setEntries(t.entries);
        setTotal(t.total);
      })
      .catch(() => {});
  }, [eventFilter, branchFilter, page]);

  useEffect(() => { loadAudit(); }, [loadAudit]);
  useAutoRefresh(loadAudit);

  const totalPages = Math.ceil(total / pageSize);

  const handleFilterChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    setter(e.target.value);
    setPage(1);
  };

  return (
    <div>
      <Header title="감사 로그" subtitle="배포/실패/원복 전체 이력 타임라인" />

      <div className="flex items-center gap-3 mb-6">
        <select value={eventFilter} onChange={handleFilterChange(setEventFilter)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
          <option value="">전체 이벤트</option>
          <option value="DEPLOY">배포</option>
          <option value="FAILURE">실패</option>
          <option value="RCA">AI 분석</option>
          <option value="ROLLBACK">원복</option>
        </select>
        <select value={branchFilter} onChange={handleFilterChange(setBranchFilter)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
          <option value="">전체 브랜치</option>
          {branches.map((b) => (
            <option key={b.name} value={b.name}>{b.name}</option>
          ))}
        </select>
        <span className="text-sm text-gray-500">총 {total}건</span>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <AuditTimelineComponent entries={entries} onSelect={setSelected} />

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-30">이전</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button key={p} onClick={() => setPage(p)}
                className={`px-3 py-1 text-sm border rounded ${p === page ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-100'}`}>
                {p}
              </button>
            ))}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-30">다음</button>
          </div>
        )}
      </div>

      {selected && <AuditDetailModal entry={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
