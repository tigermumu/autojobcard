import { apiClient } from './api'

export interface BatchContext {
  defect_list: {
    id: number
    title: string
    aircraft_number?: string | null
  }
  workcard_group: {
    configuration_id: number
    aircraft_number?: string | null
    aircraft_type?: string | null
    msn?: string | null
    amm_ipc_eff?: string | null
  }
  defect_count: number
  candidate_count: number
  latest_candidate_at?: string | null
}

export interface SavedMatchCandidate {
  id: number
  workcard_number: string
  description?: string | null
  similarity_score: number
  is_selected?: boolean
}

export interface SavedMatchResult {
  defect_record_id: number
  defect_number: string
  description_cn?: string | null
  description_en?: string | null
  candidates: SavedMatchCandidate[]
  selected_workcard_id?: number | null
}

export const matchingApi = {
  getBatchContexts: async (): Promise<BatchContext[]> => {
    return apiClient.get<BatchContext[]>('/matching/batch-contexts')
  },
  getSavedResults: async (params: { defect_list_id: number; configuration_id?: number }) => {
    return apiClient.get<{ success: boolean; results: SavedMatchResult[] }>('/matching/saved-results', params)
  }
}

