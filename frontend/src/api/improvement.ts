import { apiClient } from './client';
import type {
  ImprovementPlanRequest,
  ImprovementPlanResponse,
  PracticeQuizResponse,
} from '../types/api';

export const improvementApi = {
  createPlan: (data: ImprovementPlanRequest) =>
    apiClient.post<ImprovementPlanResponse>('/api/improvement/plans', data).then(r => r.data),

  listPlans: () =>
    apiClient.get<ImprovementPlanResponse[]>('/api/improvement/plans').then(r => r.data),

  getPlan: (id: number) =>
    apiClient.get<ImprovementPlanResponse>(`/api/improvement/plans/${id}`).then(r => r.data),

  practice: (planId: number) =>
    apiClient
      .post<PracticeQuizResponse>(`/api/improvement/plans/${planId}/practice`)
      .then(r => r.data),

  retest: (planId: number) =>
    apiClient
      .post<PracticeQuizResponse>(`/api/improvement/plans/${planId}/retest`)
      .then(r => r.data),
};
