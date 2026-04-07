import { apiClient } from './api'

export type KeywordDimension = 'main' | 'sub' | 'location' | 'orientation' | 'status' | 'action' | 'global'

export interface KeywordDictSummary {
  id: number
  configuration_id: number
  version: string
  remark?: string | null
  created_at?: string
  updated_at?: string
}

export interface KeywordDictItem {
  id: number
  dimension: KeywordDimension
  main_component?: string | null
  keyword: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export type GlobalKeyword = Pick<
  KeywordDictItem,
  'id' | 'keyword' | 'enabled' | 'created_at' | 'updated_at'
>

export interface KeywordDictDetail extends KeywordDictSummary {
  items: KeywordDictItem[]
}

export interface KeywordDictOption {
  dict_id: number
  configuration_id: number
  configuration_name: string
  version: string
  remark?: string | null
  created_at?: string
}

export interface LocalCleanWorkcardsResponse {
  success: boolean
  configuration_id: number
  dict_id: number
  dict_version: string
  total: number
  cleaned: number
  skipped: number
  message: string
}

export interface LocalWorkcardUploadRow {
  workcard_number: string
  description_cn: string
  description_en: string
}

export interface LocalCleanedWorkcard {
  workcard_number: string
  description_cn: string
  description_en: string
  main_component?: string | null
  sub_component?: string | null
  location?: string | null
  orientation?: string | null
  status?: string | null
  action?: string | null
  error?: string | null
}

export interface LocalCleanWorkcardsUploadResponse {
  success: boolean
  configuration_id: number
  dict_id: number
  dict_version: string
  total: number
  cleaned: number
  skipped: number
  cleaned_data: LocalCleanedWorkcard[]
  message: string
}

export interface LocalCleanedDefect {
  defect_record_id: number
  defect_number: string
  description_cn: string
  description_en: string
  main_component?: string | null
  sub_component?: string | null
  location?: string | null
  orientation?: string | null
  status?: string | null
  action?: string | null
}

export interface LocalCleanDefectsResponse {
  success: boolean
  defect_list_id: number
  configuration_id: number
  dict_id: number
  dict_version: string
  total: number
  cleaned: number
  skipped: number
  cleaned_data: LocalCleanedDefect[]
  message: string
}

export interface LocalCandidateWorkcard {
  id: number
  workcard_number: string
  description?: string
  description_en?: string
  similarity_score: number
}

export interface LocalMatchResult {
  defect_record_id: number
  defect_number: string
  description_cn: string
  description_en: string
  candidates: LocalCandidateWorkcard[]
}

export interface LocalMatchDefectsResponse {
  success: boolean
  defect_list_id: number
  configuration_id: number
  dict_id: number
  dict_version: string
  results: LocalMatchResult[]
  message: string
}

export interface LocalMatchStatsResponse {
  total_defects: number
  matched_defects: number
  unmatched_defects: number
  match_rate: number
}

export const localwashApi = {
  listDicts: async (configuration_id: number): Promise<KeywordDictSummary[]> => {
    return apiClient.get('/local/dicts', { configuration_id })
  },

  listDictOptions: async (): Promise<KeywordDictOption[]> => {
    return apiClient.get('/local/dicts/options')
  },

  getDict: async (dict_id: number): Promise<KeywordDictDetail> => {
    return apiClient.get(`/local/dicts/${dict_id}`)
  },

  createDictItem: async (dict_id: number, payload: { dimension: KeywordDimension; main_component?: string | null; keyword: string; enabled?: boolean }): Promise<KeywordDictItem> => {
    return apiClient.post(`/local/dict-items?dict_id=${encodeURIComponent(String(dict_id))}`, payload)
  },

  deleteDictItem: async (item_id: number): Promise<{ success: boolean }> => {
    return apiClient.delete(`/local/dict-items/${item_id}`)
  },

  importDict: async (params: {
    configuration_id: number
    version: string
    remark?: string
    file: File
  }): Promise<KeywordDictDetail> => {
    return apiClient.upload('/local/dicts/import', params.file, {
      configuration_id: params.configuration_id,
      version: params.version,
      remark: params.remark ?? '',
    })
  },

  patchDictItem: async (item_id: number, patch: { keyword?: string; main_component?: string | null; enabled?: boolean }) => {
    return apiClient.put(`/local/dict-items/${item_id}`, patch)
  },

  listGlobalKeywords: async (params?: { q?: string }): Promise<GlobalKeyword[]> => {
    return apiClient.get('/local/keywords/global', params || {})
  },

  createGlobalKeyword: async (payload: { keyword: string; enabled?: boolean }): Promise<GlobalKeyword> => {
    return apiClient.post('/local/keywords/global', {
      keyword: payload.keyword,
      enabled: payload.enabled ?? true
    })
  },

  updateGlobalKeyword: async (item_id: number, payload: { keyword?: string; enabled?: boolean }): Promise<GlobalKeyword> => {
    return apiClient.put(`/local/keywords/global/${item_id}`, payload)
  },

  deleteGlobalKeyword: async (item_id: number): Promise<{ success: boolean }> => {
    return apiClient.delete(`/local/keywords/global/${item_id}`)
  },

  cleanWorkcards: async (params: { configuration_id: number; dict_id?: number | null; cabin_layout?: string | null }): Promise<LocalCleanWorkcardsResponse> => {
    return apiClient.post('/local/clean/workcards', {
      configuration_id: params.configuration_id,
      dict_id: params.dict_id ?? null,
      cabin_layout: params.cabin_layout ?? null
    })
  },

  cleanWorkcardsUpload: async (params: { dict_id: number; rows: LocalWorkcardUploadRow[] }): Promise<LocalCleanWorkcardsUploadResponse> => {
    return apiClient.post('/local/clean/workcards/upload', {
      dict_id: params.dict_id,
      rows: params.rows,
    })
  },

  saveCleanWorkcardsUpload: async (params: { dict_id: number; rows: LocalWorkcardUploadRow[]; cabin_layout?: string | null }): Promise<LocalCleanWorkcardsResponse> => {
    return apiClient.post('/local/clean/workcards/upload/save', {
      dict_id: params.dict_id,
      rows: params.rows,
      cabin_layout: params.cabin_layout ?? null
    })
  },

  cleanDefects: async (params: { defect_list_id: number; configuration_id: number; dict_id?: number | null }): Promise<LocalCleanDefectsResponse> => {
    return apiClient.post('/local/clean/defects', {
      defect_list_id: params.defect_list_id,
      configuration_id: params.configuration_id,
      dict_id: params.dict_id ?? null
    })
  },


  matchDefects: async (params: { defect_list_id: number; configuration_id: number; dict_id?: number | null; source?: string; cabin_layout?: string | null }): Promise<LocalMatchDefectsResponse> => {
    return apiClient.post('/local/match/defects', {
      defect_list_id: params.defect_list_id,
      configuration_id: params.configuration_id,
      dict_id: params.dict_id ?? null,
      source: params.source || 'upload',
      cabin_layout: params.cabin_layout ?? null
    })
  },

  getCleanWorkcards: async (params: { configuration_id: number; dict_id?: number | null; skip?: number; limit?: number; source?: 'upload' | 'history'; cabin_layout?: string | null }): Promise<LocalCleanWorkcardsUploadResponse> => {
    return apiClient.get('/local/clean/workcards', {
      configuration_id: params.configuration_id,
      dict_id: params.dict_id ?? null,
      skip: params.skip ?? 0,
      limit: params.limit ?? 100,
      source: params.source ?? 'upload',
      cabin_layout: params.cabin_layout ?? null,
    })
  },

  getMatchStats: async (params: { defect_list_id: number; configuration_id: number; dict_id: number; cabin_layout?: string | null }): Promise<LocalMatchStatsResponse> => {
    return apiClient.get('/local/match/stats', params)
  },

  exportMatches: async (params: { defect_list_id: number; configuration_id: number; dict_id: number; cabin_layout?: string | null }): Promise<void> => {
    const blob = await apiClient.download('/local/match/export', params)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `match_results_${params.defect_list_id}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  },

  getAvailableCabinLayouts: async (params: { configuration_id: number; source?: 'upload' | 'history' }): Promise<{ cabin_layouts: string[] }> => {
    return apiClient.get('/local/clean/workcards/cabin-layouts', {
      configuration_id: params.configuration_id,
      source: params.source ?? 'upload',
    })
  },

  getAvailableCleanedDefectLists: async (params: { configuration_id: number; dict_id?: number }): Promise<{ success: boolean; defect_lists: { id: number; title: string }[] }> => {
    return apiClient.get('/local/clean/defects/available-lists', params)
  },

  getCleanedDefects: async (params: { defect_list_id: number; configuration_id: number; dict_id?: number }): Promise<LocalCleanDefectsResponse> => {
    return apiClient.get('/local/clean/defects', params)
  },

  deleteCabinLayout: async (params: { configuration_id: number; cabin_layout: string; source?: 'upload' | 'history' }): Promise<{ success: boolean; message: string }> => {
    return apiClient.delete('/local/clean/workcards/cabin-layouts', params)
  },

  deleteCleanedDefectList: async (params: { defect_list_id: number; configuration_id: number; dict_id?: number }): Promise<{ success: boolean; message: string }> => {
    return apiClient.delete('/local/clean/defects/cleaned-list', params)
  },

  exportCleanedWorkcards: async (params: { configuration_id: number; dict_id?: number | null; source?: 'upload' | 'history'; cabin_layout?: string | null }): Promise<void> => {
    const blob = await apiClient.download('/local/clean/workcards/export', params)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const layoutSuffix = params.cabin_layout ? `_${params.cabin_layout}` : ''
    link.setAttribute('download', `已清洗工卡_${params.configuration_id}${layoutSuffix}_${timestamp}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  },
}
