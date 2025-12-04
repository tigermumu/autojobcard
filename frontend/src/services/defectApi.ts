// 缺陷管理API
import { apiClient } from './api'

export interface DefectList {
  id: number
  aircraft_number: string
  title: string
  description?: string
  status: string
  configuration_id: number
  created_at: string
  updated_at?: string
}

export interface DefectRecord {
  id: number
  defect_number: string
  title: string
  description?: string
  system?: string
  component?: string
  location?: string
  severity?: string
  is_matched: boolean
  is_selected: boolean
  defect_list_id: number
  raw_data?: any
  created_at: string
}

export interface DefectListCreate {
  aircraft_number: string
  title: string
  description?: string
  configuration_id: number
}

export interface CleanDefectRequest {
  defect_list_id: number
  configuration_id: number
  limit?: number  // 可选：限制清洗数量（用于测试）
}

export interface CleanDefectResponse {
  success: boolean
  cleaned_count: number
  total_count: number
  cleaned_data: any[]
  message: string
}

export interface MatchDefectRequest {
  defect_list_id: number
  workcard_group: {
    aircraft_number?: string
    aircraft_type?: string
    msn?: string
    amm_ipc_eff?: string
    configuration_id: number
  }
}

export interface CandidateWorkCard {
  id: number
  workcard_number: string
  description?: string
  similarity_score: number
}

export interface MatchResult {
  defect_record_id: number
  defect_number: string
  description_cn?: string  // 工卡描述（中文）- 从清洗后的raw_data中获取
  description_en?: string
  candidates: CandidateWorkCard[]
}

export interface MatchDefectResponse {
  success: boolean
  task_id?: string  // 异步任务ID
  results?: MatchResult[]  // 同步返回时才有results
  message: string
  total?: number  // 总记录数
}

export interface MatchingProgress {
  task_id: string
  status: 'processing' | 'completed' | 'failed' | 'not_found'
  total: number
  completed: number
  current?: {
    defect_id: number
    defect_number: string
    description: string
  }
  statistics?: {
    matched: number
    failed: number
    candidates_found: number
  }
  error?: string
  message?: string
}

export const defectApi = {
  // 获取缺陷清单列表
  getLists: async (params?: {
    aircraft_number?: string
    status?: string
    configuration_id?: number
  }): Promise<DefectList[]> => {
    return apiClient.get<DefectList[]>('/defects/lists', params)
  },

  // 获取缺陷清单详情
  getList: async (id: number): Promise<DefectList> => {
    return apiClient.get<DefectList>(`/defects/lists/${id}`)
  },

  // 创建缺陷清单
  createList: async (data: DefectListCreate): Promise<DefectList> => {
    return apiClient.post<DefectList>('/defects/lists', data)
  },

  // 上传缺陷数据文件
  uploadDefectData: async (defect_list_id: number, file: File): Promise<any> => {
    return apiClient.upload('/defects/lists/' + defect_list_id + '/upload', file)
  },

  // 获取缺陷记录列表
  getRecords: async (defect_list_id: number, params?: {
    is_matched?: boolean
    is_selected?: boolean
  }): Promise<DefectRecord[]> => {
    return apiClient.get<DefectRecord[]>(`/defects/lists/${defect_list_id}/records`, params)
  },

  // 清洗缺陷数据
  cleanDefectData: async (data: CleanDefectRequest): Promise<CleanDefectResponse> => {
    return apiClient.post<CleanDefectResponse>('/defects/clean', data)
  },

  // 清洗缺陷数据（带进度条，使用SSE）
  cleanDefectDataWithProgress: (
    data: CleanDefectRequest,
    onProgress: (progress: {
      type: 'start' | 'progress' | 'complete' | 'error'
      current?: number
      total?: number
      percent?: number
      message?: string
      success?: boolean
      cleaned_count?: number
      total_count?: number
      cleaned_data?: any[]
    }) => void,
    onError?: (error: Error) => void
  ): void => {
    apiClient.stream(
      '/defects/clean-stream',
      data,
      onProgress,
      onError
    )
  },

  // 匹配缺陷数据与工卡
  matchDefectData: async (data: MatchDefectRequest): Promise<MatchDefectResponse> => {
    return apiClient.post<MatchDefectResponse>('/matching/batch-match', data)
  },

  // 获取匹配进度
  getMatchingProgress: async (taskId: string): Promise<MatchingProgress> => {
    return apiClient.get<MatchingProgress>(`/matching/progress/${taskId}`)
  },

  // 获取已保存的匹配结果
  getSavedResults: async (defectListId: number, configurationId?: number): Promise<{ success: boolean; results: MatchResult[] }> => {
    const params: any = { defect_list_id: defectListId }
    if (configurationId) {
      params.configuration_id = configurationId
    }
    return apiClient.get(`/matching/saved-results`, params)
  },

  // 为缺陷记录选择工卡
  selectWorkcard: async (defect_record_id: number, workcard_id: number): Promise<any> => {
    return apiClient.put(`/defects/records/${defect_record_id}/select-workcard`, { workcard_id })
  },

  // 更新已开出工卡号
  updateIssuedWorkcardNumber: async (defect_record_id: number, issued_workcard_number: string): Promise<any> => {
    return apiClient.put(`/defects/records/${defect_record_id}/issued-workcard-number`, { issued_workcard_number })
  },

  // 删除缺陷记录
  deleteDefectRecord: async (defect_record_id: number): Promise<any> => {
    return apiClient.delete(`/defects/records/${defect_record_id}`)
  },
}


