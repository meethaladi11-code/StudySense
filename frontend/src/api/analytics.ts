import { apiClient } from './client';
import type { AnalyticsOverview, TopicStat, WeakTopicSummary, AttemptSummary } from '../types/api';

export const analyticsApi = {
  overview: () =>
    apiClient.get<AnalyticsOverview>('/api/analytics/overview').then(r => r.data),

  topics: () =>
    apiClient.get<TopicStat[]>('/api/analytics/topics').then(r => r.data),

  weakTopics: () =>
    apiClient.get<WeakTopicSummary[]>('/api/analytics/weak-topics').then(r => r.data),

  history: () =>
    apiClient.get<AttemptSummary[]>('/api/analytics/history').then(r => r.data),
};
