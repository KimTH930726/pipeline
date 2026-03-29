export interface BranchInfo {
  name: string;
  is_active: boolean;
  last_commit_sha: string | null;
  last_commit_message: string | null;
}

export interface FileChange {
  path: string;
  status: string;
}

export interface DiffResponse {
  branch: string;
  file_path: string;
  diff_text: string;
}

export interface ImpactAnalysisResponse {
  risk_level: string;
  summary: string;
  affected_services: string[];
  recommendations: string[];
}
