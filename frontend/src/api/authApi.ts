import client from './client';

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  has_llm_credentials: boolean;
  llm_user_id: string | null;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
}

export interface LLMCredentials {
  client_id: string;
  client_secret: string;
  llm_user_id: string;
}

export const login = (username: string, password: string) =>
  client.post<LoginResponse>('/auth/login', { username, password }).then(r => r.data);

export const getMe = () =>
  client.get<UserInfo>('/auth/me').then(r => r.data);

export const refreshToken = (refresh_token: string) =>
  client.post<{ access_token: string }>('/auth/refresh', { refresh_token }).then(r => r.data);

export const updateLLMCredentials = (creds: LLMCredentials) =>
  client.put('/auth/me/llm-credentials', creds).then(r => r.data);

export const listUsers = () =>
  client.get<UserInfo[]>('/auth/users').then(r => r.data);

export const registerUser = (username: string, password: string, role: string = 'user') =>
  client.post<UserInfo>('/auth/register', { username, password, role }).then(r => r.data);
