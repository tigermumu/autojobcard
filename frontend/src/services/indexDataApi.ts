// 索引数据API
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
  // 获取索引数据列表
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

  // 获取单个索引数据
  getById: async (id: number): Promise<IndexData> => {
    return apiClient.get<IndexData>(`/index-data/${id}`)
  },

  // 创建索引数据
  create: async (data: IndexDataCreate): Promise<IndexData> => {
    return apiClient.post<IndexData>('/index-data/', data)
  },

  // 批量创建索引数据
  batchCreate: async (items: IndexDataCreate[]): Promise<IndexData[]> => {
    const results = await Promise.all(
      items.map(item => apiClient.post<IndexData>('/index-data/', item))
    )
    return results
  },

  // 替换索引数据（删除旧的，创建新的）
  replaceIndexData: async (configurationId: number, items: IndexDataCreate[]): Promise<IndexData[]> => {
    
    // 1. 获取该构型的所有现有数据
    const existing = await indexDataApi.getAll({ configuration_id: configurationId })
    
    // 2. 删除所有现有数据
    if (existing.length > 0) {
      await Promise.all(existing.map(item => indexDataApi.delete(item.id)))
    }
    
    // 3. 创建新数据
    if (items.length > 0) {
      const results = await Promise.all(
        items.map(item => apiClient.post<IndexData>('/index-data/', item))
      )
      return results
    }
    
    return []
  },

  // 更新索引数据
  update: async (id: number, data: IndexDataUpdate): Promise<IndexData> => {
    return apiClient.put<IndexData>(`/index-data/${id}`, data)
  },

  // 删除索引数据
  delete: async (id: number): Promise<void> => {
    return apiClient.delete(`/index-data/${id}`)
  },

  // 获取层级结构数据
  getHierarchy: async (configurationId: number): Promise<IndexDataHierarchy[]> => {
    return apiClient.get<IndexDataHierarchy[]>(
      `/index-data/configuration/${configurationId}/hierarchy`
    )
  },

  // 获取统计信息
  getStatistics: async (configurationId: number): Promise<Statistics> => {
    return apiClient.get<Statistics>(
      `/index-data/configuration/${configurationId}/statistics`
    )
  },

  // 批量导入
  batchImport: async (configurationId: number, file: File): Promise<any> => {
    return apiClient.upload(
      `/index-data/batch-import?configuration_id=${configurationId}`,
      file
    )
  },

  // 获取指定字段的唯一值
  getUniqueValues: async (
    configurationId: number,
    field: string
  ): Promise<string[]> => {
    return apiClient.get<string[]>(
      `/index-data/configuration/${configurationId}/unique-values`,
      { field }
    )
  },

  // 获取独立对照字段（前端聚合）
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
}

