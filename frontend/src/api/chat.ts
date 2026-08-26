import { api, getCsrfToken } from './client';
import type { Message } from '@/types';

export interface ChatHistoryResponse {
  session_id: string | null;
  items: Message[];
  total: number;
}

export interface DocumentUploadResponse {
  ok: boolean;
  chunks?: number;
  source_file?: string;
  error?: string;
}

export const chatApi = {
  listHistory: (characterId: string) =>
    api.get<ChatHistoryResponse>(`/chat/${characterId}/history/`),

  deleteHistoryMessage: (characterId: string, messageId: string) =>
    api.delete<void>(`/chat/${characterId}/history/${messageId}/`),

  uploadDocument: (characterId: string, file: File): Promise<DocumentUploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    const csrfToken = getCsrfToken();
    return fetch(
      `${import.meta.env.VITE_API_BASE ?? '/api'}/chat/${characterId}/documents/`,
      {
        method: 'POST',
        body: form,
        credentials: 'include',
        headers: csrfToken ? { 'X-CSRFToken': csrfToken } : undefined,
      }
    ).then(async (r) => {
      const data = await r.json().catch(() => ({})) as {
        detail?: string;
        error?: string;
        ok?: boolean;
        chunks?: number;
        source_file?: string;
      };
      if (!r.ok) {
        throw new Error(data.error || data.detail || `上传失败（HTTP ${r.status}）`);
      }
      return data as DocumentUploadResponse;
    });
  },
};
