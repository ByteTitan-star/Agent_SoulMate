import { api } from './client';
import type { User } from '@/types';

export const authApi = {
  me: () => api.get<User | null>('/auth/me/'),
  login: (username: string, password: string) =>
    api.post<{ user: User }>('/auth/login/', { username, password }),
  register: (username: string, email: string, password: string) =>
    api.post<{ user: User }>('/auth/register/', { username, email, password }),
  logout: () => api.post('/auth/logout/'),
};
