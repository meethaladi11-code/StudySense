import { apiClient } from './client';
import type {
  ChatSessionCreate,
  ChatSessionSummary,
  ChatSessionDetail,
  ChatResponse,
  SessionMessageRequest,
} from '../types/api';

export const chatApi = {
  createSession: (data: ChatSessionCreate) =>
    apiClient.post<ChatSessionSummary>('/api/chat/sessions', data).then(r => r.data),

  listSessions: () =>
    apiClient.get<ChatSessionSummary[]>('/api/chat/sessions').then(r => r.data),

  getSession: (id: number) =>
    apiClient.get<ChatSessionDetail>(`/api/chat/sessions/${id}`).then(r => r.data),

  sendMessage: (sessionId: number, data: SessionMessageRequest) =>
    apiClient
      .post<ChatResponse>(`/api/chat/sessions/${sessionId}/messages`, data)
      .then(r => r.data),
};
