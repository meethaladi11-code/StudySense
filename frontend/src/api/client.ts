/**
 * Axios API client.
 * - Reads base URL from VITE_API_BASE_URL environment variable.
 * - Automatically attaches Authorization: Bearer <token> from localStorage.
 * - On 401, clears auth state and redirects to /login.
 */

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach JWT ───────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('ss_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle 401 ─────────────────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('ss_token');
      // Redirect to login unless already there
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Extract a human-readable error message from an Axios error.
 * Handles FastAPI 422 validation errors, plain 'detail' strings,
 * and 503 Ollama-unavailable errors.
 */
export function extractErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) return 'An unexpected error occurred.';

  const status = error.response?.status;
  const detail = error.response?.data?.detail;

  if (status === 503) {
    return 'StudySense AI is currently unavailable. Make sure Ollama is running.';
  }

  if (Array.isArray(detail)) {
    return detail.map((d: { msg: string }) => d.msg).join(', ');
  }

  if (typeof detail === 'string') return detail;

  if (status === 404) return 'Resource not found.';
  if (status === 403) return 'You do not have permission to access this resource.';
  if (status === 409) return 'A conflict occurred. This resource may already exist.';
  if (status === 422) return 'Invalid request data. Please check your inputs.';
  if (status === 500) return 'A server error occurred. Please try again.';

  return error.message || 'An unexpected error occurred.';
}
