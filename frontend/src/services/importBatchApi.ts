import { apiClient } from './api'

export interface ImportBatchMetadata {
  aircraft_number: string
  workcard_number: string
  maintenance_level: string
  aircraft_type: string
  customer: string
  defect_list_id?: number
}

export interface ImportBatchItem {
  id: number
  defect_record_id?: number | null
  defect_number: string
  description_cn?: string
  description_en?: string
  workcard_number: string
  selected_workcard_id?: number | null
  similarity_score?: number | null
}

export interface ImportBatchSummary {
  id: number
  aircraft_number: string
  workcard_number: string
  maintenance_level: string
  aircraft_type: string
  customer: string
  defect_list_id?: number | null
  created_at: string
  item_count: number
}

export interface ImportBatchDetail extends ImportBatchSummary {
  items: ImportBatchItem[]
}

export const importBatchApi = {
  list: async (): Promise<ImportBatchSummary[]> => {
    return apiClient.get<ImportBatchSummary[]>('/import-batches')
  },
  getById: async (batchId: number): Promise<ImportBatchDetail> => {
    return apiClient.get<ImportBatchDetail>(`/import-batches/${batchId}`)
  },
  create: async (payload: { metadata: ImportBatchMetadata; items: Array<Omit<ImportBatchItem, 'id'>> }) => {
    return apiClient.post<ImportBatchSummary>('/import-batches', payload)
  }
}









