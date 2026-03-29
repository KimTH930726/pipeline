import client from './client';
import type { AuditTimeline, AuditEntry } from '../types/audit';

export const fetchAuditTimeline = (params?: {
  branch?: string;
  event_type?: string;
  limit?: number;
  offset?: number;
}) => client.get<AuditTimeline>('/audit/timeline', { params }).then(r => r.data);

export const fetchAuditEntry = (id: number) =>
  client.get<AuditEntry>(`/audit/${id}`).then(r => r.data);
