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

export const createBranch = (new_branch: string, base_branch: string) =>
  client.post<BranchInfo>('/git/branches', { new_branch, base_branch }).then(r => r.data);

export const deleteBranch = (branch: string) =>
  client.delete(`/git/branches/${branch}`).then(r => r.data);
