import { apiClient } from './api'

export interface WorkcardInfo {
  rid: string
  index: number
}

export interface HistoryWorkcardInfo extends WorkcardInfo {
  phase?: string
  zone?: string
  trade?: string
}

export interface LogEntry {
  step: string
  message: string
  detail?: string | null
}

export interface Artifact {
  step: string
  filename: string
  path: string
}

export interface PreviewRequest {
  tail_no: string
  src_work_order: string
  target_work_order: string
  work_group: string
  workcard_index?: number
  workcard_rid?: string
  cookies?: string
}

export interface PreviewResponse {
  workcards: WorkcardInfo[]
  history_cards: HistoryWorkcardInfo[]
  logs: LogEntry[]
  artifacts: Artifact[]
}

export interface RunRequest extends PreviewRequest {
  history_card_index?: number
  history_rid?: string
}

export interface RunResponse {
  success: boolean
  message: string
  workcards: WorkcardInfo[]
  history_cards: HistoryWorkcardInfo[]
  selected_workcard?: WorkcardInfo
  selected_history_card?: HistoryWorkcardInfo
  logs: LogEntry[]
  artifacts: Artifact[]
}

export interface TestRequest extends PreviewRequest { }

export interface TestResponse {
  success: boolean
  message: string
  logs: LogEntry[]
  artifacts: Artifact[]
}

export interface ImportDefectRequest {
  defect_record_id: number
  params: Record<string, any>
  cookies?: string
  is_test_mode?: boolean
  enable_crn_check?: boolean
}

export interface ImportDefectResponse {
  success: boolean
  message: string
  workcard_number?: string | null
  logs: LogEntry[]
  artifacts: Artifact[]
}

export interface StepInfo {
  rid: string
  index: number
  phase: string
  zone: string
  trade: string
  txt_area: string
}

export interface ImportStepsRequest {
  jobcard_number: string
  target_work_order: string  // qJcWorkOrder: 候选工卡的工卡指令号
  source_work_order: string    // qWorkorder: 导入参数配置的工作指令号 (txtWO)
  tail_no: string
  work_group: string
  step_rids?: string[]
  cookies?: string
  ref_manual?: string  // 参考手册 (CMM_REFER)，如果提供则在导入步骤后执行 updateSteps
}

export interface ImportStepsResponse {
  success: boolean
  message: string
  jc_rid?: string | null
  jc_vid?: string | null
  total_steps: number
  imported_count: number
  failed_count: number
  imported_steps: Array<{ rid: string; index: number; message: string }>
  failed_steps: Array<{ rid: string; index: number; message: string }>
  all_steps: StepInfo[]
  logs: LogEntry[]
  artifacts: Artifact[]
}

export interface ACInfoRequest {
  tail_no: string
  work_order: string
  cookies?: string
}

export interface ACInfoResponse {
  success: boolean
  data: Record<string, any>
  message: string
}

// 编写方案接口
export interface WriteStepsRequest {
  sale_wo: string       // 工作指令号 (SaleWo)
  ac_no: string         // 飞机号 (ACNo)
  jc_seq: string        // 已开出工卡号 (jcSeq)
  cmm_refer: string     // 参考手册 (CMM_REFER)
  owner_code?: string   // 客户代码 (txtCust)
  cookies?: string
  steps?: Array<{ content_en: string; trade?: string; manpower: string; man_hours: string }>
}

export interface WriteStepsResponse {
  success: boolean
  message: string
  jc_workorder_input?: string | null
  wo_rid?: string | null
  jc_rid?: string | null
  steps: string[]
  logs: string[]
}

export interface BatchWriteStepsRequest {
  items: WriteStepsRequest[]
}

export interface BatchWriteStepsItemResult {
  jc_seq: string
  success: boolean
  message: string
  steps: string[]
}

export interface BatchWriteStepsResponse {
  success: boolean
  message: string
  total: number
  success_count: number
  failed_count: number
  results: BatchWriteStepsItemResult[]
}

export interface PreviewStepsRequest {
  description_en: string
  ref_manual: string
}

export interface PreviewStepsResponse {
  success: boolean
  message: string
  steps: {
    step_number: number
    content_en: string
    content_cn?: string
    man_hours: string
    manpower: string
    trade: string
    materials: any[]
  }[]
}

export const workcardImportApi = {
  previewSteps(payload: PreviewStepsRequest) {
    return apiClient.post<PreviewStepsResponse>('/workcard-import/preview-steps', payload)
  },
  preview(payload: PreviewRequest) {
    return apiClient.post<PreviewResponse>('/workcard-import/preview', payload)
  },
  run(payload: RunRequest) {
    return apiClient.post<RunResponse>('/workcard-import/run', payload)
  },
  testConnection(payload: TestRequest) {
    return apiClient.post<TestResponse>('/workcard-import/test', payload)
  },
  importDefect(payload: ImportDefectRequest) {
    return apiClient.post<ImportDefectResponse>('/workcard-import/import-defect', payload)
  },
  importEnglishDefect(payload: ImportDefectRequest) {
    return apiClient.post<ImportDefectResponse>('/workcard-import/import-english-defect', payload)
  },
  importSteps(payload: ImportStepsRequest) {
    return apiClient.post<ImportStepsResponse>('/workcard-import/import-steps', payload)
  },
  getACInfo(payload: ACInfoRequest) {
    return apiClient.post<ACInfoResponse>('/workcard-import/ac-info', payload)
  },
  // 编写方案
  writeSteps(payload: WriteStepsRequest) {
    return apiClient.post<WriteStepsResponse>('/workcard-import/write-steps', payload)
  },
  // 批量编写方案
  batchWriteSteps(payload: BatchWriteStepsRequest) {
    return apiClient.post<BatchWriteStepsResponse>('/workcard-import/batch-write-steps', payload)
  }
}
