import client from './client';
import type { DeployStatus } from '../types/deploy';

export const triggerDeploy = (branch: string) =>
  client.post<DeployStatus>('/deploy/', { branch }).then(r => r.data);

export const fetchDeployStatus = (id: number) =>
  client.get<DeployStatus>(`/deploy/status/${id}`).then(r => r.data);

export const fetchRecentDeploys = (branch?: string) =>
  client.get<DeployStatus[]>('/deploy/recent', { params: branch ? { branch } : {} }).then(r => r.data);

export const triggerRollback = (branch: string, target_sha?: string) =>
  client.post('/rollback/', { branch, target_sha }).then(r => r.data);
