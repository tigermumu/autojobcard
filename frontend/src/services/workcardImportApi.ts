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

export interface TestRequest extends PreviewRequest {}

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

export const workcardImportApi = {
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
  importSteps(payload: ImportStepsRequest) {
    return apiClient.post<ImportStepsResponse>('/workcard-import/import-steps', payload)
  }
}

