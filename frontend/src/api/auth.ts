import { apiClient } from './client';
import type { LoginRequest, TokenResponse, UserCreate, UserResponse } from '../types/api';

export const authApi = {
  register: (data: UserCreate) =>
    apiClient.post<UserResponse>('/api/auth/register', data).then(r => r.data),

  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/api/auth/login', data).then(r => r.data),

  me: () =>
    apiClient.get<UserResponse>('/api/auth/me').then(r => r.data),
};
