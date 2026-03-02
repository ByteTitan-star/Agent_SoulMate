import { api, getCsrfToken } from './client';
import type { Character } from '@/types';

export interface CreateCharacterPayload {
  name: string;
  gender: 'male' | 'female' | 'other';
  system_prompt: string;
  opening_message?: string;
  personality: string[];
  voice_id?: string | null;
  is_public?: boolean;
  avatar_file?: File;
}

export interface UpdateCharacterPayload extends Partial<CreateCharacterPayload> {}

async function parseApiError(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => ({}));
  const detail = (body as { detail?: string }).detail;
  throw new Error(detail || fallback);
}

export const charactersApi = {
  list: (params?: { is_public?: boolean; search?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<Character[]>(`/characters/${q ? `?${q}` : ''}`);
  },
  myList: () => api.get<Character[]>('/characters/mine/'),
  get: (id: string) => api.get<Character>(`/characters/${id}/`),
  create: (payload: CreateCharacterPayload) => {
    const form = new FormData();
    form.append('name', payload.name);
    form.append('gender', payload.gender);
    form.append('system_prompt', payload.system_prompt);
    form.append('opening_message', payload.opening_message ?? '');
    form.append('personality', JSON.stringify(payload.personality));
    if (payload.voice_id != null) form.append('voice_id', payload.voice_id ?? '');
    form.append('is_public', String(payload.is_public ?? false));
    if (payload.avatar_file) form.append('avatar', payload.avatar_file);
    const csrfToken = getCsrfToken();
    return fetch(`${import.meta.env.VITE_API_BASE ?? '/api'}/characters/`, {
      method: 'POST',
      body: form,
      credentials: 'include',
      headers: csrfToken ? { 'X-CSRFToken': csrfToken } : undefined,
    }).then((r) => {
      if (!r.ok) return parseApiError(r, '创建失败');
      return r.json() as Promise<Character>;
    });
  },
  update: (id: string, payload: UpdateCharacterPayload) => {
    const form = new FormData();
    if (payload.name != null) form.append('name', payload.name);
    if (payload.gender != null) form.append('gender', payload.gender);
    if (payload.system_prompt != null) form.append('system_prompt', payload.system_prompt);
    if (payload.opening_message != null) form.append('opening_message', payload.opening_message);
    if (payload.personality != null) form.append('personality', JSON.stringify(payload.personality));
    if (payload.voice_id !== undefined) form.append('voice_id', payload.voice_id ?? '');
    if (payload.is_public !== undefined) form.append('is_public', String(payload.is_public));
    if (payload.avatar_file) form.append('avatar', payload.avatar_file);
    const csrfToken = getCsrfToken();
    return fetch(`${import.meta.env.VITE_API_BASE ?? '/api'}/characters/${id}/`, {
      method: 'PATCH',
      body: form,
      credentials: 'include',
      headers: csrfToken ? { 'X-CSRFToken': csrfToken } : undefined,
    }).then((r) => {
      if (!r.ok) return parseApiError(r, '更新失败');
      return r.json() as Promise<Character>;
    });
  },
  delete: (id: string) => api.delete(`/characters/${id}/`),
};
