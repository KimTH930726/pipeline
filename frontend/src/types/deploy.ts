export interface DeployStatus {
  id: number;
  branch: string;
  commit_sha: string | null;
  status: string;
  rolled_back: boolean;
  commit_messages: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface DeployDetail extends DeployStatus {
  build_log: string | null;
  error_log: string | null;
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
  ai_fix_prompt: string;
}
