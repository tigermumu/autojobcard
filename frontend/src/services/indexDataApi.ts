// Index Data API
import { apiClient } from './api'

export interface IndexData {
  id: number
  main_area: string
  main_component: string
  first_level_subcomponent: string
  second_level_subcomponent: string
  orientation?: string
  defect_subject?: string
  defect_description?: string
  location?: string
  quantity?: string
  configuration_id: number
  created_at: string
  updated_at?: string
}

export interface IndexDataCreate {
  main_area: string
  main_component: string
  first_level_subcomponent: string
  second_level_subcomponent: string
  orientation?: string
  defect_subject?: string
  defect_description?: string
  location?: string
  quantity?: string
  configuration_id: number
}

export interface IndexDataUpdate {
  main_area?: string
  main_component?: string
  first_level_subcomponent?: string
  second_level_subcomponent?: string
  orientation?: string
  defect_subject?: string
  defect_description?: string
  location?: string
  quantity?: string
}

export interface IndexDataHierarchy {
  main_area: string
  main_components: Array<{
    main_component: string
    first_level_subcomponents: Array<{
      first_level_subcomponent: string
      second_level_subcomponents: Array<{
        second_level_subcomponent: string
      }>
    }>
  }>
}

export interface Statistics {
  total_count: number
  areas_count: number
  components_count: number
  sub1_count: number
  sub2_count: number
}

export interface IndependentFields {
  orientation: string[]
  defect_subject: string[]
  defect_description: string[]
  location: string[]
  quantity: string[]
}

export const indexDataApi = {
  // Get index data list
  getAll: async (params?: {
    configuration_id?: number
    main_area?: string
    main_component?: string
    first_level_subcomponent?: string
    second_level_subcomponent?: string
    skip?: number
    limit?: number
  }): Promise<IndexData[]> => {
    return apiClient.get<IndexData[]>('/index-data/', params)
  },

  // Get single index data by ID
  getById: async (id: number): Promise<IndexData> => {
    return apiClient.get<IndexData>(`/index-data/${id}`)
  },

  // Create index data
  create: async (data: IndexDataCreate): Promise<IndexData> => {
    return apiClient.post<IndexData>('/index-data/', data)
  },

  // Batch create index data
  batchCreate: async (items: IndexDataCreate[]): Promise<IndexData[]> => {
    const results = await Promise.all(
      items.map(item => apiClient.post<IndexData>('/index-data/', item))
    )
    return results
  },

  // Replace index data (delete old, create new)
  replaceIndexData: async (configurationId: number, items: IndexDataCreate[]): Promise<any> => {
    // Call new backend interface for atomic replacement
    return apiClient.put(`/index-data/configuration/${configurationId}/replace`, {
      data: items
    })
  },

  // Update index data
  update: async (id: number, data: IndexDataUpdate): Promise<IndexData> => {
    return apiClient.put<IndexData>(`/index-data/${id}`, data)
  },

  // Delete index data
  delete: async (id: number): Promise<void> => {
    return apiClient.delete(`/index-data/${id}`)
  },

  // Get hierarchy data
  getHierarchy: async (configurationId: number): Promise<IndexDataHierarchy[]> => {
    return apiClient.get<IndexDataHierarchy[]>(
      `/index-data/configuration/${configurationId}/hierarchy`
    )
  },

  // Get statistics
  getStatistics: async (configurationId: number): Promise<Statistics> => {
    return apiClient.get<Statistics>(
      `/index-data/configuration/${configurationId}/statistics`
    )
  },

  // Batch import (default: replace mode)
  batchImport: async (configurationId: number, file: File, replace: boolean = true): Promise<any> => {
    return apiClient.upload(
      `/index-data/batch-import?configuration_id=${configurationId}&replace=${replace}`,
      file
    )
  },

  // Get unique values for a field
  getUniqueValues: async (
    configurationId: number,
    field: string
  ): Promise<string[]> => {
    return apiClient.get<string[]>(
      `/index-data/configuration/${configurationId}/unique-values`,
      { field }
    )
  },

  // Get independent fields (frontend aggregation)
  getIndependentFields: async (configurationId: number): Promise<IndependentFields> => {
    const allData = await indexDataApi.getAll({ configuration_id: configurationId })

    const independent: any = {
      orientation: [],
      defectSubject: [],
      defectDescription: [],
      location: [],
      quantity: [],
    }

    allData.forEach(item => {
      if (item.orientation && !independent.orientation.includes(item.orientation)) {
        independent.orientation.push(item.orientation)
      }
      if (item.defect_subject && !independent.defectSubject.includes(item.defect_subject)) {
        independent.defectSubject.push(item.defect_subject)
      }
      if (item.defect_description && !independent.defectDescription.includes(item.defect_description)) {
        independent.defectDescription.push(item.defect_description)
      }
      if (item.location && !independent.location.includes(item.location)) {
        independent.location.push(item.location)
      }
      if (item.quantity && !independent.quantity.includes(item.quantity)) {
        independent.quantity.push(item.quantity)
      }
    })

    return independent
  },

  // Export index data to Excel
  exportToExcel: async (configurationId: number): Promise<void> => {
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const BASE_URL = `${API_BASE_URL}/index-data`
    const url = `${BASE_URL}/configuration/${configurationId}/export`
    const response = await fetch(url)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
    }

    // Get filename from Content-Disposition header
    // Support both RFC 5987 format (filename*=UTF-8''...) and standard format
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `索引数据_${configurationId}.xlsx`
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
          // Handle URL encoding
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
}
