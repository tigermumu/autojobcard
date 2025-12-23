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

  // 导出独立索引字段（field_mapping）到Excel
  exportFieldMappingToExcel: async (configurationId: number): Promise<void> => {
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const url = `${API_BASE_URL}/configurations/${configurationId}/field-mapping/export`
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
    }
    
    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `独立索引字段_${configurationId}.xlsx`
    if (contentDisposition) {
      // Try RFC 5987 format first (filename*=UTF-8''...)
      const rfc5987Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i)
      if (rfc5987Match && rfc5987Match[1]) {
        filename = decodeURIComponent(rfc5987Match[1])
      } else {
        // Fallback to standard format
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '')
          try {
            filename = decodeURIComponent(filename)
          } catch (e) {
            // If decoding fails, use as-is
          }
        }
      }
    }
    
    // Download file
    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  },

  // 从Excel导入独立索引字段（field_mapping）
  importFieldMappingFromExcel: async (configurationId: number, file: File): Promise<any> => {
    return apiClient.upload(
      `/configurations/${configurationId}/field-mapping/import`,
      file
    )
  },
}



