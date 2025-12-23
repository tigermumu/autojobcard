// 工卡管理API
import { apiClient } from './api'

export interface WorkCard {
  id: number
  workcard_number: string
  title: string
  description?: string
  system: string
  component: string
  location?: string
  action?: string
  configuration_id: number
  workcard_type_id: number
  // 单机构型识别字段
  aircraft_number?: string
  aircraft_type?: string
  msn?: string
  amm_ipc_eff?: string
  // 清洗后的索引字段
  main_area?: string
  main_component?: string
  first_level_subcomponent?: string
  second_level_subcomponent?: string
  orientation?: string
  defect_subject?: string
  defect_description?: string
  location_index?: string
  quantity?: string
  // 清洗状态
  is_cleaned: boolean
  cleaning_confidence: number
  cleaning_notes?: string
  created_at: string
  updated_at?: string
}

export interface WorkCardCreate {
  workcard_number: string
  title: string
  description?: string
  system: string
  component: string
  location?: string
  action?: string
  configuration_id: number
  workcard_type_id: number
}

export interface WorkCardUpdate {
  workcard_number?: string
  title?: string
  description?: string
  system?: string
  component?: string
  location?: string
  action?: string
  // 单机构型识别字段
  aircraft_number?: string
  aircraft_type?: string
  msn?: string
  amm_ipc_eff?: string
  // 清洗后的索引字段
  main_area?: string
  main_component?: string
  first_level_subcomponent?: string
  second_level_subcomponent?: string
  orientation?: string
  defect_subject?: string
  defect_description?: string
  location_index?: string
  quantity?: string
  is_cleaned?: boolean
  cleaning_confidence?: number
  cleaning_notes?: string
}

export interface CleanWorkCardRequest {
  raw_data: any[]
  configuration_id: number
}

export interface CleanWorkCardResponse {
  success: boolean
  cleaned_count: number
  total_count: number
  data: any[]
  error?: string
}

export interface SaveCleanedWorkCardRequest {
  cleaned_data: any[]
  configuration_id: number
  aircraft_number?: string
  aircraft_type?: string
  msn?: string
  amm_ipc_eff?: string
}

export interface SaveCleanedWorkCardResponse {
  success: boolean
  saved_count: number
  total_count: number
  skipped_count: number
  errors: string[]
  message: string
}

export interface WorkCardGroup {
  aircraft_number?: string
  aircraft_type?: string
  msn?: string
  amm_ipc_eff?: string
  configuration_id: number
  count: number
  min_id: number
}

export const workcardApi = {
  // 获取工卡列表
  getAll: async (params?: {
    configuration_id?: number
    system?: string
    component?: string
    is_cleaned?: boolean
    skip?: number
    limit?: number
  }): Promise<WorkCard[]> => {
    return apiClient.get<WorkCard[]>('/workcards/', params)
  },

  // 获取单个工卡
  getById: async (id: number): Promise<WorkCard> => {
    return apiClient.get<WorkCard>(`/workcards/${id}`)
  },

  // 创建工卡
  create: async (data: WorkCardCreate): Promise<WorkCard> => {
    return apiClient.post<WorkCard>('/workcards/', data)
  },

  // 更新工卡
  update: async (id: number, data: WorkCardUpdate): Promise<WorkCard> => {
    return apiClient.put<WorkCard>(`/workcards/${id}`, data)
  },

  // 删除工卡
  delete: async (id: number): Promise<void> => {
    return apiClient.delete(`/workcards/${id}`)
  },

  // 清洗工卡数据
  cleanData: async (data: CleanWorkCardRequest): Promise<CleanWorkCardResponse> => {
    return apiClient.post<CleanWorkCardResponse>('/workcards/clean', data)
  },

  // 保存清洗后的工卡数据到数据库
  saveCleanedData: async (data: SaveCleanedWorkCardRequest): Promise<SaveCleanedWorkCardResponse> => {
    return apiClient.post<SaveCleanedWorkCardResponse>('/workcards/save-cleaned', data)
  },

  // 获取工卡分组列表
  getGroups: async (is_cleaned: boolean = true): Promise<WorkCardGroup[]> => {
    // 传递布尔值字符串，FastAPI会自动转换为布尔值
    return apiClient.get<WorkCardGroup[]>('/workcards/groups', { 
      is_cleaned: is_cleaned.toString() 
    })
  },

  // 根据识别字段获取同一组下的所有工卡
  getByGroup: async (params: {
    aircraft_number?: string
    aircraft_type?: string
    msn?: string
    amm_ipc_eff?: string
    configuration_id?: number
  }): Promise<WorkCard[]> => {
    return apiClient.get<WorkCard[]>('/workcards/by-group', params)
  },

  // 删除整个工卡分组
  deleteGroup: async (params: {
    aircraft_number?: string
    aircraft_type?: string
    msn?: string
    amm_ipc_eff?: string
    configuration_id?: number
  }): Promise<{ success: boolean; message: string; deleted_count: number }> => {
    return apiClient.delete<{ success: boolean; message: string; deleted_count: number }>(
      '/workcards/groups',
      params as any
    )
  },

  // 导出工卡分组数据到Excel
  exportGroupToExcel: async (params: {
    aircraft_number?: string
    aircraft_type?: string
    msn?: string
    amm_ipc_eff?: string
    configuration_id?: number
  }): Promise<void> => {
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const queryParams = new URLSearchParams()
    if (params.aircraft_number) queryParams.append('aircraft_number', params.aircraft_number)
    if (params.aircraft_type) queryParams.append('aircraft_type', params.aircraft_type)
    if (params.msn) queryParams.append('msn', params.msn)
    if (params.amm_ipc_eff) queryParams.append('amm_ipc_eff', params.amm_ipc_eff)
    if (params.configuration_id) queryParams.append('configuration_id', String(params.configuration_id))
    
    const url = `${API_BASE_URL}/workcards/by-group/export?${queryParams.toString()}`
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
    }
    
    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `工卡数据表.xlsx`
    if (contentDisposition) {
      const rfc5987Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i)
      if (rfc5987Match && rfc5987Match[1]) {
        filename = decodeURIComponent(rfc5987Match[1])
      } else {
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

  // 从Excel导入工卡数据到分组
  importGroupFromExcel: async (
    file: File,
    params: {
      aircraft_number?: string
      aircraft_type?: string
      msn?: string
      amm_ipc_eff?: string
      configuration_id?: number
      replace?: boolean
    }
  ): Promise<any> => {
    const queryParams = new URLSearchParams()
    if (params.aircraft_number) queryParams.append('aircraft_number', params.aircraft_number)
    if (params.aircraft_type) queryParams.append('aircraft_type', params.aircraft_type)
    if (params.msn) queryParams.append('msn', params.msn)
    if (params.amm_ipc_eff) queryParams.append('amm_ipc_eff', params.amm_ipc_eff)
    if (params.configuration_id) queryParams.append('configuration_id', String(params.configuration_id))
    if (params.replace !== undefined) queryParams.append('replace', String(params.replace))
    
    return apiClient.upload(
      `/workcards/by-group/import?${queryParams.toString()}`,
      file
    )
  },
}


