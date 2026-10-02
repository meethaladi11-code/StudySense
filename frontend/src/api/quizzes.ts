import { apiClient } from './client';
import type {
  QuizGenerateRequest,
  QuizSummary,
  QuizTakeResponse,
  QuizSubmitRequest,
  QuizSubmitResponse,
  AttemptSummary,
} from '../types/api';

export const quizzesApi = {
  generate: (data: QuizGenerateRequest) =>
    apiClient.post<QuizSummary>('/api/quizzes/generate', data).then(r => r.data),

  list: () =>
    apiClient.get<QuizSummary[]>('/api/quizzes').then(r => r.data),

  get: (id: number) =>
    apiClient.get<QuizSummary>(`/api/quizzes/${id}`).then(r => r.data),

  take: (id: number) =>
    apiClient.get<QuizTakeResponse>(`/api/quizzes/${id}/take`).then(r => r.data),

  submit: (id: number, data: QuizSubmitRequest) =>
    apiClient.post<QuizSubmitResponse>(`/api/quizzes/${id}/submit`, data).then(r => r.data),

  attempts: (id: number) =>
    apiClient.get<AttemptSummary[]>(`/api/quizzes/${id}/attempts`).then(r => r.data),
};
