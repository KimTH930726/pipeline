export interface DeployStatus {
  id: number;
  branch: string;
  commit_sha: string | null;
  status: string;
  rolled_back: boolean;
  acted_by: string | null;
  commit_messages: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface DeployDetail extends DeployStatus {
  build_log: string | null;
  error_log: string | null;
}

export interface BuildLogMessage {
  type: 'log_line' | 'status' | 'rca' | 'stage';
  data: string | RCAReport;
  stream?: string;
  exit_code?: number;
  stage?: string;
  status?: string;
}

export type StageKey = 'CONFLICT_CHECK' | 'BUILD_VALIDATION' | 'MERGE' | 'DOCKER_RESTART';
export type StageStatus = 'pending' | 'started' | 'completed' | 'failed';

export interface StageInfo {
  key: StageKey;
  label: string;
  status: StageStatus;
}

export interface RCAReport {
  root_cause: string;
  affected_files: string[];
  suggested_fix: string;
  confidence_score: number;
  ai_fix_prompt: string;
}
