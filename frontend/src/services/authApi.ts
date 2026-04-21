import { apiClient } from './api'

export interface UserProfile {
  id: number
  username: string
  display_name?: string | null
  role_name?: string | null
  permissions: string[]
  is_active: boolean
  is_superuser: boolean
  last_login_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: UserProfile
}

export interface MessageResponse {
  message: string
}

export interface UserCreatePayload {
  username: string
  display_name?: string
  role_name?: string
  password: string
  permissions: string[]
  is_active: boolean
  is_superuser: boolean
}

export interface UserUpdatePayload {
  display_name?: string
  role_name?: string
  permissions?: string[]
  is_active?: boolean
  is_superuser?: boolean
}

export const authApi = {
  login: (payload: { username: string; password: string }) =>
    apiClient.post<LoginResponse>('/auth/login', payload),
  me: () => apiClient.get<UserProfile>('/auth/me'),
  changePassword: (payload: { old_password: string; new_password: string }) =>
    apiClient.post<MessageResponse>('/auth/change-password', payload),
  listUsers: () => apiClient.get<{ items: UserProfile[] }>('/users'),
  createUser: (payload: UserCreatePayload) => apiClient.post<UserProfile>('/users', payload),
  updateUser: (userId: number, payload: UserUpdatePayload) => apiClient.put<UserProfile>(`/users/${userId}`, payload),
  updatePassword: (userId: number, password: string) =>
    apiClient.put<UserProfile>(`/users/${userId}/password`, { password }),
  deleteUser: (userId: number) => apiClient.delete<{ message: string }>(`/users/${userId}`),
}
