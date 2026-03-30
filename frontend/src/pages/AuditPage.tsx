import { useState, useEffect } from 'react';
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

  useEffect(() => {
    fetchBranches().then(setBranches).catch(() => {});
  }, []);

  useEffect(() => {
    fetchAuditTimeline({
      event_type: eventFilter || undefined,
      branch: branchFilter || undefined,
      limit: 50,
    })
      .then((t) => {
        setEntries(t.entries);
        setTotal(t.total);
      })
      .catch(() => {});
  }, [eventFilter, branchFilter]);

  return (
    <div>
      <Header title="감사 로그" subtitle="배포/실패/원복 전체 이력 타임라인" />

      <div className="flex items-center gap-3 mb-6">
        <select
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="">전체 이벤트</option>
          <option value="DEPLOY">배포</option>
          <option value="FAILURE">실패</option>
          <option value="RCA">AI 분석</option>
          <option value="ROLLBACK">원복</option>
        </select>
        <select
          value={branchFilter}
          onChange={(e) => setBranchFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="">전체 브랜치</option>
          {branches.map((b) => (
            <option key={b.name} value={b.name}>{b.name}</option>
          ))}
        </select>
        <span className="text-sm text-gray-500">총 {total}건</span>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <AuditTimelineComponent entries={entries} onSelect={setSelected} />
      </div>

      {selected && <AuditDetailModal entry={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
