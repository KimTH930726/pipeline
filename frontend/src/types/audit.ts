export interface AuditEntry {
  id: number;
  event_type: string;
  branch: string;
  commit_sha: string | null;
  ai_report: Record<string, unknown> | null;
  metadata_: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditTimeline {
  entries: AuditEntry[];
  total: number;
}
