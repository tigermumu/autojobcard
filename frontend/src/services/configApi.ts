// 构型管理API
import { apiClient } from './api'

export interface Configuration {
  id: number
  name: string
  aircraft_type?: string  // 机型
  msn?: string  // MSN
  model?: string  // MODEL
  vartab?: string  // VARTAB
  customer?: string  // 客户
  amm_ipc_eff?: string  // AMM/IPC EFF
  version?: string  // 版本
  description?: string
  field_mapping?: any
  created_at: string
  updated_at?: string
}

export interface ConfigurationCreate {
  name: string
  aircraft_type?: string  // 机型
  msn?: string  // MSN
  model?: string  // MODEL
  vartab?: string  // VARTAB
  customer?: string  // 客户
  amm_ipc_eff?: string  // AMM/IPC EFF
  version?: string  // 版本
  description?: string
}

export interface ConfigurationUpdate {
  name?: string
  aircraft_type?: string  // 机型
  msn?: string  // MSN
  model?: string  // MODEL
  vartab?: string  // VARTAB
  customer?: string  // 客户
  amm_ipc_eff?: string  // AMM/IPC EFF
  version?: string  // 版本
  description?: string
  field_mapping?: any
}

export const configApi = {
  // 获取所有构型
  getAll: async (): Promise<Configuration[]> => {
    return apiClient.get<Configuration[]>('/configurations/')
  },

  // 获取单个构型
  getById: async (id: number): Promise<Configuration> => {
    return apiClient.get<Configuration>(`/configurations/${id}`)
  },

  // 创建构型
  create: async (data: ConfigurationCreate): Promise<Configuration> => {
    return apiClient.post<Configuration>('/configurations/', data)
  },

  // 更新构型
  update: async (id: number, data: ConfigurationUpdate): Promise<Configuration> => {
    return apiClient.put<Configuration>(`/configurations/${id}`, data)
  },

  // 删除构型
  delete: async (id: number): Promise<void> => {
    return apiClient.delete(`/configurations/${id}`)
  },

  // 上传索引文件
  uploadIndexFile: async (configurationId: number, file: File): Promise<any> => {
    return apiClient.upload(
      `/configurations/${configurationId}/upload-index`,
      file
    )
  },
}



