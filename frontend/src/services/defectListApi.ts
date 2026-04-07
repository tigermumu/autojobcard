/**
 * 缺陷清单处理 API
 */

import axios from 'axios'

const API_BASE = '/api/v1/defect-list'

// ==================== 类型定义 ====================

export interface IndexItem {
  id: number
  comp_pn: string | null
  comp_desc: string | null
  comp_cmm: string | null
  comp_cmm_rev: string | null
  remark: string | null
}

export interface IndexInfo {
  id: number
  name: string
  sale_wo: string
  ac_no: string
  row_count: number
  created_at: string
}

export interface IndexDataResponse {
  success: boolean
  message: string
  id?: number
  sale_wo?: string
  ac_no?: string
  row_count?: number
  items?: IndexItem[]
}

export interface IndexListResponse {
  success: boolean
  data: IndexInfo[]
}

export interface ProcessStats {
  total: number
  matched: number
  apiSuccess: number
  apiFail: number
}

// ==================== 索引表 API ====================

/**
 * 获取所有索引表列表
 */
export async function listIndexes(): Promise<IndexListResponse> {
  const response = await axios.get<IndexListResponse>(`${API_BASE}/index/list`)
  return response.data
}

/**
 * 上传索引表
 */
export async function uploadIndex(
  file: File,
  saleWo: string,
  acNo: string,
  yearMonth: string
): Promise<IndexDataResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('sale_wo', saleWo)
  formData.append('ac_no', acNo)
  formData.append('year_month', yearMonth)

  const response = await axios.post<IndexDataResponse>(
    `${API_BASE}/index/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  )
  return response.data
}

/**
 * 获取索引表详情（包含所有数据项）
 */
export async function getIndex(indexId: number): Promise<IndexDataResponse> {
  const response = await axios.get<IndexDataResponse>(`${API_BASE}/index/${indexId}`)
  return response.data
}

/**
 * 删除索引表
 */
export async function deleteIndex(indexId: number): Promise<{ success: boolean; message: string }> {
  const response = await axios.delete(`${API_BASE}/index/${indexId}`)
  return response.data
}

// ==================== 索引项 CRUD API ====================

export interface IndexItemCreate {
  comp_pn?: string
  comp_desc?: string
  comp_cmm?: string
  comp_cmm_rev?: string
  remark?: string
}

/**
 * 添加索引项
 */
export async function createIndexItem(indexId: number, data: IndexItemCreate): Promise<IndexItem> {
  const response = await axios.post<IndexItem>(`${API_BASE}/index/${indexId}/item`, data)
  return response.data
}

/**
 * 更新索引项
 */
export async function updateIndexItem(itemId: number, data: IndexItemCreate): Promise<IndexItem> {
  const response = await axios.put<IndexItem>(`${API_BASE}/index/item/${itemId}`, data)
  return response.data
}

/**
 * 删除索引项
 */
export async function deleteIndexItem(itemId: number): Promise<{ success: boolean; message: string }> {
  const response = await axios.delete(`${API_BASE}/index/item/${itemId}`)
  return response.data
}

// ==================== 缺陷表处理 API ====================

/**
 * 使用指定索引表处理缺陷表并下载结果
 */
export async function processDefects(
  indexId: number,
  file: File,
  cookie?: string
): Promise<{ blob: Blob; stats: ProcessStats }> {
  const formData = new FormData()
  formData.append('file', file)
  if (cookie) {
    formData.append('cookie', cookie)
  }

  const response = await axios.post(`${API_BASE}/process/${indexId}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    responseType: 'blob'
  })

  const stats: ProcessStats = {
    total: parseInt(response.headers['x-process-total'] || '0', 10),
    matched: parseInt(response.headers['x-process-matched'] || '0', 10),
    apiSuccess: parseInt(response.headers['x-process-api-success'] || '0', 10),
    apiFail: parseInt(response.headers['x-process-api-fail'] || '0', 10)
  }

  return {
    blob: response.data,
    stats
  }
}

/**
 * 下载文件辅助函数
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
