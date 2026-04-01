const BASE_URL = '/api';

function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = `${BASE_URL}${path}`;
  if (!params) return url;
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `${url}?${qs}` : url;
}

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<{ data: T }> {
  if (response.status === 401 && !response.url.includes('/auth/login')) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    return Promise.reject(new Error('Unauthorized'));
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    return Promise.reject(Object.assign(new Error(response.statusText), { response: { status: response.status, data: error } }));
  }
  if (response.status === 204) {
    return { data: undefined as T };
  }
  const data = await response.json() as T;
  return { data };
}

const client = {
  get<T = unknown>(url: string, config?: { params?: Record<string, unknown> }): Promise<{ data: T }> {
    return fetch(buildUrl(url, config?.params), { headers: getHeaders() }).then(r => handleResponse<T>(r));
  },
  post<T = unknown>(url: string, body?: unknown): Promise<{ data: T }> {
    return fetch(buildUrl(url), { method: 'POST', headers: getHeaders(), body: body != null ? JSON.stringify(body) : undefined }).then(r => handleResponse<T>(r));
  },
  put<T = unknown>(url: string, body?: unknown): Promise<{ data: T }> {
    return fetch(buildUrl(url), { method: 'PUT', headers: getHeaders(), body: body != null ? JSON.stringify(body) : undefined }).then(r => handleResponse<T>(r));
  },
  delete<T = unknown>(url: string): Promise<{ data: T }> {
    return fetch(buildUrl(url), { method: 'DELETE', headers: getHeaders() }).then(r => handleResponse<T>(r));
  },
};

export default client;
