export interface DeployStatus {
  id: number;
  branch: string;
  commit_sha: string | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface BuildLogMessage {
  type: 'log_line' | 'status' | 'rca';
  data: string | RCAReport;
  stream?: string;
  exit_code?: number;
}

export interface RCAReport {
  root_cause: string;
  affected_files: string[];
  suggested_fix: string;
  confidence_score: number;
}
