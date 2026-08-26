import { api } from './client';

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  can_create_character: boolean;
  can_publish_character: boolean;
  date_joined: string;
  character_count: number;
}

export interface UpdateUserPermissionPayload {
  can_create_character?: boolean;
  can_publish_character?: boolean;
}

export const adminApi = {
  listUsers: (): Promise<AdminUser[]> =>
    api.get('/admin/users/'),

  updateUser: (id: string, payload: UpdateUserPermissionPayload): Promise<AdminUser> =>
    api.patch(`/admin/users/${id}/`, payload),
};
