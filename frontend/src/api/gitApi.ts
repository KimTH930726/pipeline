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
