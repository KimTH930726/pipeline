import client from './client';

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  has_api_key: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
}

export const login = (username: string, password: string) =>
  client.post<LoginResponse>('/auth/login', { username, password }).then(r => r.data);

export const getMe = () =>
  client.get<UserInfo>('/auth/me').then(r => r.data);

export const refreshToken = (refresh_token: string) =>
  client.post<{ access_token: string }>('/auth/refresh', { refresh_token }).then(r => r.data);

export const updateApiKey = (llm_api_key: string) =>
  client.put('/auth/me/api-key', { llm_api_key }).then(r => r.data);

export const listUsers = () =>
  client.get<UserInfo[]>('/auth/users').then(r => r.data);

export const registerUser = (username: string, password: string, role: string = 'user') =>
  client.post<UserInfo>('/auth/register', { username, password, role }).then(r => r.data);
