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
  workcard_number?: string | null  // 候选工卡，Excel中没有数据时可以留空
  selected_workcard_id?: number | null
  similarity_score?: number | null
  issued_workcard_number?: string | null
  // New fields
  reference_workcard_number?: string | null
  reference_workcard_item?: string | null
  area?: string | null
  zone_number?: string | null
  loc?: string | null
  qty?: number | null
  comp_pn?: string | null
  keywords_1?: string | null
  keywords_2?: string | null
  candidate_description_en?: string | null  // 历史工卡描述（英文），来自Excel的 Candidate Workcard Description (English) 列
  candidate_description_cn?: string | null  // 历史工卡描述（中文），来自Excel的 Candidate Workcard Description (Chinese) 列
  ref_manual?: string | null  // 参考手册 (CMM_REFER)，来自Excel的 参考手册 列
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
  },
  delete: async (batchId: number): Promise<void> => {
    return apiClient.delete(`/import-batches/${batchId}`)
  }
}







