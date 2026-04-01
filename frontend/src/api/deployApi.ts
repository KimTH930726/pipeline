import client from './client';
import type { DeployStatus, DeployDetail } from '../types/deploy';

export const triggerDeploy = (branch: string) =>
  client.post<DeployStatus>('/deploy/', { branch }).then(r => r.data);

export const fetchDeployStatus = (id: number) =>
  client.get<DeployDetail>(`/deploy/status/${id}`).then(r => r.data);

export interface DeployPage {
  items: DeployStatus[];
  total: number;
  page: number;
  size: number;
}

export const fetchRecentDeploys = (page = 1, size = 10, branch?: string, status?: string, dateFrom?: string, dateTo?: string) =>
  client.get<DeployPage>('/deploy/recent', { params: {
    page, size,
    ...(branch ? { branch } : {}),
    ...(status ? { status } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
  } }).then(r => r.data);

export interface RollbackResult {
  status: string;
  reverted_to: string;
  new_commit: string;
  deployment_id: number | null;
}

export const triggerRollback = (branch: string, target_sha?: string) =>
  client.post<RollbackResult>('/rollback/', { branch, target_sha }).then(r => r.data);

export const markRolledBack = (id: number) =>
  client.post(`/deploy/status/${id}/rolled-back`).then(r => r.data);

export interface DeployCompare {
  from: { id: number; branch: string; commit_sha: string };
  to: { id: number; branch: string; commit_sha: string };
  diff_text: string;
}

export const compareDeploys = (idFrom: number, idTo: number) =>
  client.get<DeployCompare>(`/deploy/compare/${idFrom}/${idTo}`).then(r => r.data);
