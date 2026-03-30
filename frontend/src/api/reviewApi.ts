import client from './client';

export interface ReviewResponse {
  id: number;
  branch: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  comment: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export const requestReview = (branch: string) =>
  client.post<ReviewResponse>('/review/request', { branch }).then(r => r.data);

export const approveReview = (branch: string, comment?: string) =>
  client.post<ReviewResponse>('/review/approve', { branch, comment }).then(r => r.data);

export const rejectReview = (branch: string, comment?: string) =>
  client.post<ReviewResponse>('/review/reject', { branch, comment }).then(r => r.data);

export const getReviewStatus = (branch: string) =>
  client.get<ReviewResponse>(`/review/status/${branch}`).then(r => r.data);

export const listApprovedReviews = () =>
  client.get<ReviewResponse[]>('/review/approved').then(r => r.data);

export const listAllReviews = () =>
  client.get<ReviewResponse[]>('/review/list').then(r => r.data);
