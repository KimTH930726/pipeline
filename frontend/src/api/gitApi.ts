import client from './client';
import type { BranchInfo, FileChange, DiffResponse, ImpactAnalysisResponse } from '../types/git';

export const fetchBranches = () =>
  client.get<BranchInfo[]>('/git/branches').then(r => r.data);

export const fetchChangedFiles = (branch: string) =>
  client.get<FileChange[]>('/git/branches/files', { params: { branch } }).then(r => r.data);

export const fetchDiff = (branch: string, path: string) =>
  client.get<DiffResponse>('/git/diff', { params: { branch, path } }).then(r => r.data);

export const analyzeImpact = (branch: string, file_paths?: string[]) =>
  client.post<ImpactAnalysisResponse>('/analysis/impact', { branch, file_paths }).then(r => r.data);

export interface CodeReviewComment {
  file_path: string;
  line: number | null;
  severity: 'critical' | 'warning' | 'info';
  category: string;
  message: string;
  suggested_code: string;
}

export interface CodeReviewResponse {
  summary: string;
  comments: CodeReviewComment[];
  overall_quality: 'good' | 'needs_improvement' | 'poor';
}

export const reviewCode = (branch: string, file_paths?: string[]) =>
  client.post<CodeReviewResponse>('/analysis/review', { branch, file_paths }).then(r => r.data);

export interface ConflictResolution {
  file_path: string;
  original_content: string;
  resolved_content: string;
  explanation: string;
}

export interface MergeConflictResponse {
  has_conflicts: boolean;
  conflicting_files: string[];
  resolutions: ConflictResolution[];
  summary: string;
}

export const checkConflicts = (branch: string) =>
  client.post<MergeConflictResponse>('/analysis/conflicts', { branch }).then(r => r.data);

export const applyResolution = (branch: string, resolutions: Record<string, string>) =>
  client.post('/analysis/conflicts/apply', { branch, resolutions }).then(r => r.data);

export const createBranch = (new_branch: string, base_branch: string) =>
  client.post<BranchInfo>('/git/branches', { new_branch, base_branch }).then(r => r.data);

export const deleteBranch = (branch: string) =>
  client.delete(`/git/branches/${branch}`).then(r => r.data);
