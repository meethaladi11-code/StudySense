import { apiClient } from './client';
import type { DocumentResponse } from '../types/api';

export const documentsApi = {
  list: () =>
    apiClient.get<DocumentResponse[]>('/api/documents').then(r => r.data),

  get: (id: number) =>
    apiClient.get<DocumentResponse>(`/api/documents/${id}`).then(r => r.data),

  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post<DocumentResponse>('/api/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    }).then(r => r.data);
  },
};
