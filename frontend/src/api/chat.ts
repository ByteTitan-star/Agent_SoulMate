import { api } from './client';
import type { Message } from '@/types';

export interface ChatHistoryResponse {
  session_id: string | null;
  items: Message[];
  total: number;
}

export const chatApi = {
  listHistory: (characterId: string) =>
    api.get<ChatHistoryResponse>(`/chat/${characterId}/history/`),

  deleteHistoryMessage: (characterId: string, messageId: string) =>
    api.delete<void>(`/chat/${characterId}/history/${messageId}/`),
};
