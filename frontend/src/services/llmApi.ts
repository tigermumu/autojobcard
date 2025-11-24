import { apiClient } from './api'

export interface LLMModelInfo {
  value: string
  label: string
  description: string
  provider: string
}

export interface ListModelsResponse {
  data: LLMModelInfo[]
  current_model: LLMModelInfo
}

export interface SelectModelResponse {
  message: string
  current_model: LLMModelInfo
}

export const fetchLLMModels = async (): Promise<ListModelsResponse> => {
  return apiClient.get<ListModelsResponse>('/llm/models')
}

export const selectLLMModel = async (model: string): Promise<SelectModelResponse> => {
  return apiClient.post<SelectModelResponse>('/llm/models/select', { model })
}










